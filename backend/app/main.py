import time
import logging
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from backend.app.config import Config
from backend.app.database import init_db, get_db_connection
from backend.app.simulator import StadiumSimulator
from backend.app.models import (
    FanChatRequest, StaffChatRequest, ChatResponse,
    StadiumStatus, GateStatus, ZoneStatus, PlainLanguageAlert
)
from backend.app.llm import query_stadium_assistant, execute_with_retry_and_circuit_breaker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="EktaAI API",
    description="GenAI-powered stadium operations assistant backend for FIFA World Cup 2026",
    version="1.0.0"
)

from fastapi.exceptions import ResponseValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    logger.error(f"Response validation error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Response format validation error."}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom In-Memory Token/Request Rate Limiter
class IPBasedRateLimiter:
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.request_timestamps = defaultdict(list)

    def is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        # Filter timestamps within window
        self.request_timestamps[ip] = [t for t in self.request_timestamps[ip] if now - t < self.window]
        
        if len(self.request_timestamps[ip]) >= self.limit:
            return True
            
        self.request_timestamps[ip].append(now)
        return False

chat_limiter = IPBasedRateLimiter(limit=Config.RATE_LIMIT_LIMIT, window=Config.RATE_LIMIT_WINDOW)

# Startup / Shutdown Events
active_simulator = None

@app.on_event("startup")
def startup_event():
    global active_simulator
    logger.info("Initializing database...")
    init_db()
    
    logger.info("Starting Digital Twin Simulator...")
    if active_simulator is None or not active_simulator.is_alive():
        active_simulator = StadiumSimulator()
        active_simulator.start()

@app.on_event("shutdown")
def shutdown_event():
    global active_simulator
    if active_simulator and active_simulator.is_alive():
        logger.info("Stopping Digital Twin Simulator...")
        active_simulator.stop()

# --- Health / Base ---
@app.get("/")
def read_root():
    return {"app": "EktaAI API", "status": "healthy", "version": "1.0.0"}

# --- Stadium State API ---

@app.get("/api/v1/stadium/gates", response_model=List[GateStatus])
def get_gates():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, status, congestion_level, zone_id FROM gates")
        gates = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return gates
    except Exception as e:
        logger.error(f"Error in get_gates: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving gates.")

@app.get("/api/v1/stadium/zones", response_model=List[ZoneStatus])
def get_zones():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type, capacity, current_crowd, density FROM zones")
        zones = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return zones
    except Exception as e:
        logger.error(f"Error in get_zones: {e}")
        raise HTTPException(status_code=500, detail="Database connection error while retrieving zones.")

@app.get("/api/v1/stadium/status", response_model=StadiumStatus)
def get_stadium_status():
    gates = get_gates()
    zones = get_zones()
    return {
        "gates": gates,
        "zones": zones,
        "timestamp": time.time()
    }

# --- Fan Assistant Chat API ---

@app.post("/api/v1/chat/fan", response_model=ChatResponse)
async def chat_fan(request: FanChatRequest, req: Request):
    # Security: Sanitization & Input Validation
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or only whitespace."
        )
    sanitized_message = request.message.replace("<", "&lt;").replace(">", "&gt;").strip()
    
    # Validate language parameter
    lang = request.language.strip().lower() if request.language else "en"
    if lang not in ["en", "es"]:
        lang = "en"
    
    # Rate Limiting
    client_ip = req.client.host if req.client else "unknown"
    if chat_limiter.is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Limit is {Config.RATE_LIMIT_LIMIT} per {Config.RATE_LIMIT_WINDOW} seconds."
        )
        
    try:
        response_data = query_stadium_assistant(sanitized_message, is_staff=False)
        return response_data
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in chat_fan: {e}")
        raise HTTPException(status_code=500, detail="Internal assistant error.")

# --- Staff Dashboard Chat API ---

@app.post("/api/v1/chat/staff", response_model=ChatResponse)
async def chat_staff(request: StaffChatRequest):
    # Security: Sanitization & Input Validation
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or only whitespace."
        )
    sanitized_message = request.message.replace("<", "&lt;").replace(">", "&gt;").strip()
    try:
        response_data = query_stadium_assistant(sanitized_message, is_staff=True)
        return response_data
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in chat_staff: {e}")
        raise HTTPException(status_code=500, detail="Internal operations portal error.")

from backend.app.llm_client import GeminiLLMClient, MockLLMClient
import json

# Caching dict for LLM generated alerts
ALERT_CACHE = {}

def get_deterministic_alert_fallback(alert_data: dict) -> tuple[str, str]:
    """Helper to build fallback message and recommended action based on old templates."""
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
    # 1. Check Cache
    cache_key = (
        alert_data.get("type"),
        alert_data.get("id"),
        alert_data.get("status"),
        alert_data.get("severity")
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
            llm_res = client.generate(system_prompt, prompt, tools=[])
        except Exception as e:
            logger.error(f"Injected client alert generation failed: {e}")

    # Core Failover Sequence
    # A. Try Gemini
    if llm_res is None and Config.GEMINI_API_KEY:
        llm_res, success = execute_with_retry_and_circuit_breaker(
            "gemini",
            lambda: GeminiLLMClient(Config.GEMINI_API_KEY),
            system_prompt,
            prompt,
            tools=[],
            response_format={"type": "json_object"}
        )

    # B. Try Groq
    if llm_res is None and Config.GROQ_API_KEY:
        from backend.app.llm_client import GroqLLMClient
        llm_res, success = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(Config.GROQ_API_KEY),
            system_prompt,
            prompt,
            tools=[],
            response_format={"type": "json_object"}
        )

    # C. Try Mock
    if llm_res is None:
        client_instance = MockLLMClient()
        llm_res = client_instance.generate(system_prompt, prompt, tools=[])

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
    from backend.app.llm_client import GeminiLLMClient, MockLLMClient
    
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
    if Config.GEMINI_API_KEY:
        try:
            client_instance = GeminiLLMClient(Config.GEMINI_API_KEY)
            llm_res = client_instance.generate(system_prompt, prompt, tools=[], response_format={"type": "json_object"})
        except Exception as e:
            logger.error(f"Gemini batch alert generation failed: {e}. Trying Groq fallback.")
            
    # B. Try Groq
    if llm_res is None and Config.GROQ_API_KEY:
        try:
            from backend.app.llm_client import GroqLLMClient
            client_instance = GroqLLMClient(Config.GROQ_API_KEY)
            llm_res = client_instance.generate(system_prompt, prompt, tools=[], response_format={"type": "json_object"})
        except Exception as e:
            logger.error(f"Groq batch alert generation failed: {e}. Falling back to Mock client.")
            
    # C. Try Mock
    if llm_res is None:
        client_instance = MockLLMClient()
        llm_res = client_instance.generate(system_prompt, prompt, tools=[])
        
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

# --- Operational Intelligence Alerts API ---

@app.get("/api/v1/staff/alerts", response_model=List[PlainLanguageAlert])
def get_staff_alerts():
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
        raise HTTPException(status_code=500, detail="Database connection error while retrieving alerts.")
    
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
            anomaly.get("severity")
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

