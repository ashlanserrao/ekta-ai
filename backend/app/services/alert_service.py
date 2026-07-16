import json
import logging
from backend.app.config import settings
from backend.app.database import get_db_connection
from backend.app.llm_client import GeminiLLMClient, MockLLMClient

logger = logging.getLogger("alert_service")

# Caching dict for LLM generated alerts
ALERT_CACHE = {}

def get_deterministic_alert_fallback(alert_data: dict) -> tuple[str, str]:
    """Helper to build fallback message and recommended action based on templates."""
    alert_type = alert_data.get("type")
    severity = alert_data.get("severity")
    
    if alert_type == "zone":
        name = alert_data.get("name")
        density = alert_data.get("density", 0.0)
        current_crowd = alert_data.get("current_crowd", 0)
        density_pct = int(density * 100)
        
        if severity == "critical":
            message = f"Critical congestion in {name} ({density_pct}% density, {current_crowd} occupants)."
            action = f"De-escalate crowd: redirect entries away from gate associated with {name}. Dispatch stewards to guide crowds to adjacent, less dense zones."
        else:
            message = f"Moderate congestion building in {name} ({density_pct}% density)."
            action = "Monitor crowd flow rate. Ensure secondary emergency paths are clear."
            
    elif alert_type == "gate":
        name = alert_data.get("name")
        status = alert_data.get("status")
        
        if status == "closed":
            message = f"{name} is currently CLOSED."
            action = "Ensure directional display monitors redirect arrivals to the closest open gate."
        else: # emergency_only
            message = f"{name} is set to EMERGENCY EXIT ONLY."
            action = "Inform shuttle controllers and security personnel immediately. Prevent inbound fans from queueing."
            
    else: # normal info alert
        message = "All stadium zones and gates are operating within normal parameters."
        action = "Maintain standard entry checkpoints monitoring."
        
    return message, action

def extract_and_parse_json(text: str) -> dict:
    """Robust parser to extract and load JSON from LLM responses."""
    import re
    text_clean = text.strip()
    
    # 1. Try direct parsing first
    try:
        return json.loads(text_clean)
    except Exception:
        pass
        
    # 2. Try to find json block wrapped in markdown ```json ... ```
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text_clean)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass
            
    # 3. Fallback: Search for the first '{' and last '}' to extract raw JSON
    first_curly = text_clean.find('{')
    last_curly = text_clean.rfind('}')
    if first_curly != -1 and last_curly != -1 and last_curly > first_curly:
        json_candidate = text_clean[first_curly:last_curly+1]
        try:
            return json.loads(json_candidate)
        except Exception:
            pass
            
    raise ValueError("Could not locate a valid JSON structure in response.")

def generate_alert_with_llm(alert_data: dict, client=None) -> tuple[str, str]:
    from backend.app.services.orchestrator import execute_with_retry_and_circuit_breaker
    
    # 1. Check Cache
    cache_key = (
        alert_data.get("type"),
        alert_data.get("id"),
        alert_data.get("status"),
        alert_data.get("severity"),
        alert_data.get("density"),
        alert_data.get("current_crowd")
    )
    if cache_key in ALERT_CACHE:
        return ALERT_CACHE[cache_key]
        
    fallback_msg, fallback_action = get_deterministic_alert_fallback(alert_data)
    
    # 2. Get LLM client & run alert generation with failover
    system_prompt = (
        "You are EktaAI, an operational intelligence engine for FIFA World Cup 2026. "
        "You translate raw, structured stadium sensor data into professional, clear plain-language alerts "
        "and action items. Always return response in JSON format with keys: message, recommended_action."
    )
    prompt = (
        f"Sensor alert data to translate:\n"
        f"{json.dumps(alert_data)}\n\n"
        f"Generate a plain-language alert message and a recommended mitigation action. Return JSON format."
    )

    llm_res = None

    # If client is injected directly, try running it
    if client is not None:
        try:
            llm_res = client.generate(system_prompt, prompt, tools=[], mode="alert_translation")
        except Exception as e:
            logger.error(f"Injected client alert generation failed: {e}")

    # Core Failover Sequence
    # A. Try Gemini
    if llm_res is None and settings.GEMINI_API_KEY:
        logger.info("Alert Translation: Attempting with Gemini provider.")
        result = execute_with_retry_and_circuit_breaker(
            "gemini",
            lambda: GeminiLLMClient(settings.GEMINI_API_KEY),
            system_prompt,
            prompt,
            tools=[],
            response_format={"type": "json_object"},
            mode="alert_translation"
        )
        if isinstance(result, tuple) and len(result) == 2:
            llm_res, success = result
        else:
            llm_res, success = None, False

    # B. Try Groq
    if llm_res is None and settings.GROQ_API_KEY:
        logger.info("Alert Translation: Attempting with Groq provider.")
        from backend.app.llm_client import GroqLLMClient
        result = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(settings.GROQ_API_KEY),
            system_prompt,
            prompt,
            tools=[],
            response_format={"type": "json_object"},
            mode="alert_translation"
        )
        if isinstance(result, tuple) and len(result) == 2:
            llm_res, success = result
        else:
            llm_res, success = None, False

    # C. Try Mock
    if llm_res is None:
        logger.info("Alert Translation: Selecting Mock client (Fallback)")
        client_instance = MockLLMClient()
        llm_res = client_instance.generate(system_prompt, prompt, tools=[], mode="alert_translation")

    # 3. Parse JSON response from selected LLM
    try:
        raw_content = getattr(llm_res, 'reply', 'None')
        logger.info(f"Raw alert LLM response content: {raw_content}")
        
        data = extract_and_parse_json(raw_content)
        msg = data.get("message", fallback_msg)
        act = data.get("recommended_action", fallback_action)
        
        ALERT_CACHE[cache_key] = (msg, act)
        return msg, act
    except Exception as e:
        if llm_res and hasattr(llm_res, 'reply'):
            reply_text = llm_res.reply
            if "[GenAI Alert]" in reply_text:
                parts = reply_text.split("[GenAI Action]")
                msg = parts[0].replace("[GenAI Alert]", "").strip()
                act = parts[1].strip() if len(parts) > 1 else fallback_action
                ALERT_CACHE[cache_key] = (msg, act)
                return msg, act
                
        logger.error(f"Error parsing LLM response JSON: {e}. Raw response content was: {getattr(llm_res, 'reply', 'None')}. Using deterministic fallback.")
        return fallback_msg, fallback_action

def generate_alerts_batch_with_llm(anomalies_list: list) -> list:
    """Generates alerts for a list of anomalies in a single LLM request with failover."""
    from backend.app.services.orchestrator import execute_with_retry_and_circuit_breaker
    
    # Generate fallbacks for each anomaly in list
    fallbacks = []
    for anomaly in anomalies_list:
        msg, act = get_deterministic_alert_fallback(anomaly)
        fallbacks.append({"message": msg, "recommended_action": act})
        
    system_prompt = (
        "You are EktaAI, an operational intelligence engine for FIFA World Cup 2026. "
        "You translate a list of raw stadium sensor anomalies into professional plain-language alerts "
        "and action items. Always return response in JSON format. The response must be a JSON object "
        "containing an 'alerts' key, which maps to a list of alert objects. Each alert object "
        "must have exactly two keys: 'message' and 'recommended_action', corresponding order-by-order "
        "to the list of anomalies in the prompt."
    )
    
    prompt = (
        f"List of raw anomalies to translate:\n"
        f"{json.dumps(anomalies_list)}\n\n"
        f"Translate each anomaly in order. Return a JSON object with keys: alerts (list of objects with message and recommended_action)."
    )
    
    llm_res = None
    
    # A. Try Gemini
    if llm_res is None and settings.GEMINI_API_KEY:
        logger.info("Batch Alerts: Attempting with Gemini provider.")
        result = execute_with_retry_and_circuit_breaker(
            "gemini",
            lambda: GeminiLLMClient(settings.GEMINI_API_KEY),
            system_prompt,
            prompt,
            tools=[],
            response_format={"type": "json_object"},
            mode="alert_translation"
        )
        if isinstance(result, tuple) and len(result) == 2:
            llm_res, success = result
        else:
            llm_res, success = None, False

    # B. Try Groq
    if llm_res is None and settings.GROQ_API_KEY:
        logger.info("Batch Alerts: Attempting with Groq provider.")
        from backend.app.llm_client import GroqLLMClient
        result = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(settings.GROQ_API_KEY),
            system_prompt,
            prompt,
            tools=[],
            response_format={"type": "json_object"},
            mode="alert_translation"
        )
        if isinstance(result, tuple) and len(result) == 2:
            llm_res, success = result
        else:
            llm_res, success = None, False
            
    # C. Try Mock
    if llm_res is None:
        logger.info("Batch Alerts: Selecting Mock client (Fallback)")
        client_instance = MockLLMClient()
        llm_res = client_instance.generate(system_prompt, prompt, tools=[], mode="alert_translation")
        
    # Parse response
    try:
        raw_content = getattr(llm_res, 'reply', 'None')
        logger.info(f"Raw batch alerts LLM response content: {raw_content}")
        
        parsed_data = extract_and_parse_json(raw_content)
        alerts_list = parsed_data.get("alerts", [])
        
        result = []
        for idx, anomaly in enumerate(anomalies_list):
            if idx < len(alerts_list):
                gen_item = alerts_list[idx]
                msg = gen_item.get("message") or fallbacks[idx]["message"]
                act = gen_item.get("recommended_action") or fallbacks[idx]["recommended_action"]
                result.append({"message": msg, "recommended_action": act})
            else:
                result.append(fallbacks[idx])
        return result
    except Exception as e:
        logger.error(f"Error parsing batch LLM response: {e}. Raw response content was: {getattr(llm_res, 'reply', 'None')}. Using deterministic fallbacks.")
        return fallbacks

def get_staff_alerts() -> list:
    """Business logic for checking gate and zone anomalies and generating plain language mitigation guides."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, name, density, current_crowd FROM zones")
        zones = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT id, name, status FROM gates")
        gates = [dict(row) for row in cursor.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"Database error in get_staff_alerts: {e}")
        raise e
    
    anomalies_list = []
    
    # 1. Check for high density zones
    for z in zones:
        if z["density"] > 0.85:
            anomalies_list.append({
                "type": "zone",
                "id": z["id"],
                "name": z["name"],
                "density": z["density"],
                "current_crowd": z["current_crowd"],
                "severity": "critical"
            })
        elif z["density"] > 0.70:
            anomalies_list.append({
                "type": "zone",
                "id": z["id"],
                "name": z["name"],
                "density": z["density"],
                "current_crowd": z["current_crowd"],
                "severity": "warning"
            })
            
    # 2. Check for closed gates
    for g in gates:
        if g["status"] == "closed":
            anomalies_list.append({
                "type": "gate",
                "id": g["id"],
                "name": g["name"],
                "status": g["status"],
                "severity": "warning"
            })
        elif g["status"] == "emergency_only":
            anomalies_list.append({
                "type": "gate",
                "id": g["id"],
                "name": g["name"],
                "status": g["status"],
                "severity": "critical"
            })
            
    # 3. If no anomalies, return standard operational status
    if not anomalies_list:
        anomalies_list.append({
            "type": "normal",
            "severity": "info"
        })
        
    alerts_result = []
    uncached_items = []
    
    # 4. Check cache
    for anomaly in anomalies_list:
        cache_key = (
            anomaly.get("type"),
            anomaly.get("id"),
            anomaly.get("status"),
            anomaly.get("severity"),
            anomaly.get("density"),
            anomaly.get("current_crowd")
        )
        
        if cache_key in ALERT_CACHE:
            msg, act = ALERT_CACHE[cache_key]
            alerts_result.append({
                "id": f"alert_{anomaly.get('type')}_{anomaly.get('id')}" if anomaly.get("type") != "normal" else "alert_normal",
                "severity": anomaly["severity"],
                "message": msg,
                "recommended_action": act
            })
        else:
            uncached_items.append((anomaly, cache_key))
            
    # 5. Process uncached items in a single batch request
    if uncached_items:
        batch_anomalies = [item[0] for item in uncached_items]
        generated_results = generate_alerts_batch_with_llm(batch_anomalies)
        
        for (anomaly, cache_key), gen_item in zip(uncached_items, generated_results):
            msg = gen_item["message"]
            act = gen_item["recommended_action"]
            ALERT_CACHE[cache_key] = (msg, act)
            
            alerts_result.append({
                "id": f"alert_{anomaly.get('type')}_{anomaly.get('id')}" if anomaly.get("type") != "normal" else "alert_normal",
                "severity": anomaly["severity"],
                "message": msg,
                "recommended_action": act
            })
            
    return alerts_result
