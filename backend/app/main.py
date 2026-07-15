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
from backend.app.llm import query_stadium_assistant

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="EktaAI API",
    description="GenAI-powered stadium operations assistant backend for FIFA World Cup 2026",
    version="1.0.0"
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, status, congestion_level, zone_id FROM gates")
    gates = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return gates

@app.get("/api/v1/stadium/zones", response_model=List[ZoneStatus])
def get_zones():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, type, capacity, current_crowd, density FROM zones")
    zones = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return zones

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
    # Min length is 1, max is 500, validated by Pydantic
    # Sanitize inputs to prevent prompt injection or execution
    sanitized_message = request.message.replace("<", "&lt;").replace(">", "&gt;").strip()
    
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
    except Exception as e:
        logger.error(f"Error in chat_fan: {e}")
        raise HTTPException(status_code=500, detail="Internal assistant error.")

# --- Staff Dashboard Chat API ---

@app.post("/api/v1/chat/staff", response_model=ChatResponse)
async def chat_staff(request: StaffChatRequest):
    # Sanitize inputs
    sanitized_message = request.message.replace("<", "&lt;").replace(">", "&gt;").strip()
    try:
        response_data = query_stadium_assistant(sanitized_message, is_staff=True)
        return response_data
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

def generate_alert_with_llm(alert_data: dict, client=None) -> tuple[str, str]:
    # 1. Check Cache
    cache_key = (
        alert_data.get("type"),
        alert_data.get("id"),
        alert_data.get("density"),
        alert_data.get("current_crowd"),
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
        try:
            client_instance = GeminiLLMClient(Config.GEMINI_API_KEY)
            llm_res = client_instance.generate(system_prompt, prompt, tools=[])
        except Exception as e:
            logger.error(f"Gemini alert generation failed: {e}. Trying Groq fallback.")

    # B. Try Groq
    if llm_res is None and Config.GROQ_API_KEY:
        try:
            from backend.app.llm_client import GroqLLMClient
            client_instance = GroqLLMClient(Config.GROQ_API_KEY)
            llm_res = client_instance.generate(system_prompt, prompt, tools=[])
        except Exception as e:
            logger.error(f"Groq alert generation failed: {e}. Falling back to Mock client.")

    # C. Try Mock
    if llm_res is None:
        client_instance = MockLLMClient()
        llm_res = client_instance.generate(system_prompt, prompt, tools=[])

    # 3. Parse JSON response from selected LLM
    try:
        clean_reply = llm_res.reply.strip()
        if clean_reply.startswith("```json"):
            clean_reply = clean_reply[7:]
        if clean_reply.endswith("```"):
            clean_reply = clean_reply[:-3]
        clean_reply = clean_reply.strip()
        
        data = json.loads(clean_reply)
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
                
        logger.error(f"Error parsing LLM response JSON: {e}. Using deterministic fallback.")
        return fallback_msg, fallback_action

# --- Operational Intelligence Alerts API ---

@app.get("/api/v1/staff/alerts", response_model=List[PlainLanguageAlert])
def get_staff_alerts():
    alerts = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Check for high density zones
    cursor.execute("SELECT id, name, density, current_crowd FROM zones")
    zones = cursor.fetchall()
    for z in zones:
        if z["density"] > 0.85:
            alert_data = {
                "type": "zone",
                "id": z["id"],
                "name": z["name"],
                "density": z["density"],
                "current_crowd": z["current_crowd"],
                "severity": "critical"
            }
            msg, act = generate_alert_with_llm(alert_data)
            alerts.append({
                "id": f"alert_zone_{z['id']}",
                "severity": "critical",
                "message": msg,
                "recommended_action": act
            })
        elif z["density"] > 0.70:
            alert_data = {
                "type": "zone",
                "id": z["id"],
                "name": z["name"],
                "density": z["density"],
                "current_crowd": z["current_crowd"],
                "severity": "warning"
            }
            msg, act = generate_alert_with_llm(alert_data)
            alerts.append({
                "id": f"alert_zone_{z['id']}",
                "severity": "warning",
                "message": msg,
                "recommended_action": act
            })
            
    # 2. Check for closed gates
    cursor.execute("SELECT id, name, status FROM gates")
    gates = cursor.fetchall()
    for g in gates:
        if g["status"] == "closed":
            alert_data = {
                "type": "gate",
                "id": g["id"],
                "name": g["name"],
                "status": g["status"],
                "severity": "warning"
            }
            msg, act = generate_alert_with_llm(alert_data)
            alerts.append({
                "id": f"alert_gate_{g['id']}",
                "severity": "warning",
                "message": msg,
                "recommended_action": act
            })
        elif g["status"] == "emergency_only":
            alert_data = {
                "type": "gate",
                "id": g["id"],
                "name": g["name"],
                "status": g["status"],
                "severity": "critical"
            }
            msg, act = generate_alert_with_llm(alert_data)
            alerts.append({
                "id": f"alert_gate_{g['id']}",
                "severity": "critical",
                "message": msg,
                "recommended_action": act
            })
            
    conn.close()
    
    # If no alerts, return a standard operational status
    if not alerts:
        alert_data = {
            "type": "normal",
            "severity": "info"
        }
        msg, act = generate_alert_with_llm(alert_data)
        alerts.append({
            "id": "alert_normal",
            "severity": "info",
            "message": msg,
            "recommended_action": act
        })
        
    return alerts

