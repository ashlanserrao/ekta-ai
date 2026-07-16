import json
import logging
import re
from typing import List, Tuple
from backend.app.config import settings
from backend.app.llm_client import MockLLMClient
from backend.app.database import get_db_connection
from backend.app.models import PlainLanguageAlert

logger = logging.getLogger("services.alert")

# Local cache for translated alerts (keyed by anomaly serialization)
ALERT_CACHE = {}

def get_deterministic_alert_fallback(anomaly: dict) -> Tuple[str, str]:
    """Generates standard deterministic alert messages if LLM service is offline."""
    if anomaly.get("type") == "zone":
        name = anomaly.get("name", "Unknown Zone")
        density = anomaly.get("density", 0.0)
        current = anomaly.get("current_crowd", 0)
        severity = anomaly.get("severity", "info")
        if severity == "critical":
            msg = f"[System Alert] Critical crowd surge detected at {name}. Occupancy has reached {int(density*100)}% capacity ({current} fans)."
            act = "[Steward Action] Immediately halt incoming ticket validation at adjacent turnstiles. Re-route arrival streams toward alternative entrances and deploy crowd control officers."
        else:
            msg = f"[System Alert] Crowd density is climbing at {name}, now at {int(density*100)}%."
            act = "[Steward Action] Activate secondary warning signage and instruct stewards to monitor local walkways for bottlenecks."
    elif anomaly.get("type") == "gate":
        name = anomaly.get("name", "Unknown Gate")
        status = anomaly.get("status", "open")
        if status == "closed":
            msg = f"[System Alert] Checkpoint status change: {name} is CLOSED."
            act = "Activate digital detour guidance screens. Direct arriving spectators to nearest open gate immediately."
        else:
            msg = f"[System Alert] Access restriction: {name} has transitioned to EMERGENCY EXIT ONLY."
            act = "Coordinate with emergency response units and notify nearby shuttle loops to suspend drops at this gate."
    else:
        msg = "[System Alert] General operational alert triggered."
        act = "[Steward Action] Maintain standard stadium surveillance checks."
    return msg, act

def extract_and_parse_json(text: str) -> dict:
    """Helper to cleanly parse JSON dictionary output block from raw LLM responses."""
    # Find JSON blocks
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Failed parsing JSON from text: {e}")

def generate_alert_with_llm(anomaly: dict, client=None) -> Tuple[str, str]:
    """Translates a raw anomaly dictionary into natural language message and steward recommendation."""
    from backend.app.services.orchestrator import execute_with_retry_and_circuit_breaker
    
    cache_key = f"{anomaly.get('id')}_{anomaly.get('status', '')}_{anomaly.get('density', 0.0)}"
    if cache_key in ALERT_CACHE:
        return ALERT_CACHE[cache_key]

    fallback_msg, fallback_action = get_deterministic_alert_fallback(anomaly)
    
    system_prompt = (
        "You are EktaAI, an operational intelligence engine for FIFA World Cup 2026. "
        "You translate a raw stadium sensor anomaly dictionary into a professional, clear plain-language "
        "stadium alert message and a recommended action item for stadium stewards. "
        "Always return response in JSON format. The response must be a JSON object containing exactly two keys: "
        "'message' (str) and 'recommended_action' (str)."
    )
    
    prompt = (
        f"Raw Anomaly Details:\n"
        f"{json.dumps(anomaly)}\n\n"
        f"Translate into JSON with keys 'message' and 'recommended_action'."
    )
    
    llm_res = None
    
    # If client is injected directly, try running it
    if client is not None:
        try:
            llm_res = client.generate(system_prompt, prompt, tools=[], mode="alert_translation")
        except Exception as e:
            logger.error(f"Injected client alert generation failed: {e}")

    # Core Failover Sequence
    # A. Try Groq
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

    # B. Try Mock
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
    
    # A. Try Groq
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
            
    # B. Try Mock
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
                msg = alerts_list[idx].get("message", fallbacks[idx]["message"])
                act = alerts_list[idx].get("recommended_action", fallbacks[idx]["recommended_action"])
                result.append({"id": anomaly["id"], "message": msg, "recommended_action": act, "severity": anomaly["severity"]})
            else:
                result.append({"id": anomaly["id"], "message": fallbacks[idx]["message"], "recommended_action": fallbacks[idx]["recommended_action"], "severity": anomaly["severity"]})
        return result
    except Exception as e:
        logger.error(f"Batch alerts parsing failed: {e}. Falling back to deterministic outputs.")
        result = []
        for idx, anomaly in enumerate(anomalies_list):
            result.append({"id": anomaly["id"], "message": fallbacks[idx]["message"], "recommended_action": fallbacks[idx]["recommended_action"], "severity": anomaly["severity"]})
        return result

def get_staff_alerts() -> List[PlainLanguageAlert]:
    """Scans digital twin databases, triggers alerts on anomalies, and updates registry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    anomalies = []
    
    # 1. Check for closed gates
    cursor.execute("SELECT id, name, status, congestion_level FROM gates WHERE status = 'closed'")
    for row in cursor.fetchall():
        anomalies.append({
            "type": "gate",
            "id": row["id"],
            "name": row["name"],
            "status": row["status"],
            "congestion": row["congestion_level"],
            "severity": "medium"
        })
        
    # 2. Check for high density zones
    cursor.execute("SELECT id, name, type, capacity, current_crowd, density FROM zones WHERE density >= 0.70")
    for row in cursor.fetchall():
        anomalies.append({
            "type": "zone",
            "id": row["id"],
            "name": row["name"],
            "capacity": row["capacity"],
            "current_crowd": row["current_crowd"],
            "density": row["density"],
            "severity": "critical" if row["density"] >= 0.85 else "medium"
        })
        
    conn.close()
    
    if not anomalies:
        return []
        
    try:
        # Generate plain language translations in batch using GenAI engine
        return generate_alerts_batch_with_llm(anomalies)
    except Exception as e:
        logger.error(f"GenAI batch alerts translation failed: {e}. Using local fallback translations.")
        fallback_alerts = []
        for anomaly in anomalies:
            msg, act = get_deterministic_alert_fallback(anomaly)
            fallback_alerts.append({
                "id": anomaly["id"],
                "message": msg,
                "recommended_action": act,
                "severity": anomaly["severity"]
            })
        return fallback_alerts
