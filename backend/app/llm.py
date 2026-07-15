import os
import json
import logging
import re
import time
from backend.app.config import Config
from backend.app.database import get_db_connection
from backend.app.rag import get_rag

logger = logging.getLogger("llm")

from backend.app.llm_client import GeminiLLMClient, MockLLMClient, ToolCall, LLMResult

def is_quota_or_rate_limit_error(error_msg: str) -> bool:
    """Helper to detect quota exhaustion, rate limits, or auth errors."""
    error_lower = error_msg.lower()
    return any(w in error_lower for w in [
        "quota", 
        "exhausted", 
        "limit", 
        "429", 
        "too many requests",
        "resource_exhausted",
        "billing",
        "api key",
        "invalid key",
        "unauthorized",
        "auth",
        "credentials"
    ])

def execute_with_retry_and_circuit_breaker(provider_name: str, client_initializer, system_prompt: str, user_message: str, tools: list, response_format: dict = None) -> tuple:
    """
    Executes an LLM call with a safe 2-time retry (3 attempts total) for transient issues, 
    and immediately trips a circuit breaker on daily quota/auth errors, or after consecutive failures.
    Returns: (LLMResult or None, success boolean)
    """
    if provider_name == "gemini" and Config.GEMINI_EXHAUSTED:
        logger.info("Gemini circuit breaker is active. Skipping Gemini.")
        return None, False
    if provider_name == "groq" and Config.GROQ_EXHAUSTED:
        logger.info("Groq circuit breaker is active. Skipping Groq.")
        return None, False
        
    attempts = 3
    backoff = 0.5
    
    for attempt in range(1, attempts + 1):
        try:
            client = client_initializer()
            logger.info(f"[{provider_name.upper()}] Attempt {attempt} of {attempts}...")
            llm_res = client.generate(system_prompt, user_message, tools, response_format=response_format)
            return llm_res, True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{provider_name.upper()}] Attempt {attempt} failed: {error_msg}")
            
            if is_quota_or_rate_limit_error(error_msg):
                logger.warning(f"[{provider_name.upper()}] Quota/Rate Limit/Auth error detected! Tripping circuit breaker immediately.")
                if provider_name == "gemini":
                    Config.GEMINI_EXHAUSTED = True
                elif provider_name == "groq":
                    Config.GROQ_EXHAUSTED = True
                break
                
            if attempt < attempts:
                logger.info(f"Transient error detected. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
                backoff *= 3
            else:
                logger.warning(f"[{provider_name.upper()}] Failed all {attempts} attempts. Tripping circuit breaker for safety.")
                if provider_name == "gemini":
                    Config.GEMINI_EXHAUSTED = True
                elif provider_name == "groq":
                    Config.GROQ_EXHAUSTED = True

# --- Define Python Tool Functions ---

def get_crowd_density(zone: str) -> dict:
    """
    Gets the current crowd density and capacity information for a specific stadium zone or concourse.
    :param zone: The zone ID (e.g. 'Zone-A', 'Zone-B', 'Zone-C') or zone name.
    """
    if not zone:
        return {"error": "Zone name or ID must be provided. Available: Zone-A, Zone-B, Zone-C, Zone-D, Zone-VIP"}
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, capacity, current_crowd, density FROM zones WHERE id = ? OR name LIKE ?",
            (zone, f"%{zone}%")
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return {"error": f"Zone '{zone}' not found. Available: Zone-A, Zone-B, Zone-C, Zone-D, Zone-VIP"}
    except Exception as e:
        logger.error(f"Database error in get_crowd_density: {e}")
        return {"error": "Unable to retrieve zone details at this time."}

def get_gate_status() -> list:
    """
    Gets the status (open/closed) and congestion level of all stadium gates.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, status, congestion_level, zone_id FROM gates")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Database error in get_gate_status: {e}")
        return []

def get_route(from_location: str, to_location: str, accessibility_required: bool = False) -> dict:
    """
    Retrieves the routing path between two locations, filtering for wheelchair accessibility if required.
    :param from_location: Start point (e.g., 'Gate 1', 'Gate 2')
    :param to_location: Destination point (e.g., 'Section 102', 'Section 204')
    :param accessibility_required: True if step-free accessible route is needed.
    """
    if not from_location or not to_location:
        return {"error": "Both start location (from_location) and destination (to_location) must be provided."}
        
    from backend.app.routing import find_path
    
    def resolve_node_name(query: str) -> str:
        if not query:
            return ""
        q_lower = query.lower().strip()
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM nodes")
            nodes = [r["id"] for r in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logger.error(f"Database error in resolve_node_name: {e}")
            return query
            
        # Check case-insensitive exact or substring match
        for node in nodes:
            if node.lower() == q_lower:
                return node
        for node in nodes:
            if node.lower() in q_lower or q_lower in node.lower():
                return node
        return query
        
    resolved_from = resolve_node_name(from_location)
    resolved_to = resolve_node_name(to_location)
    
    try:
        path = find_path(resolved_from, resolved_to, accessibility_required)
    except Exception as e:
        logger.error(f"Error computing path in find_path: {e}")
        return {"error": "Unable to calculate route path at this time."}
        
    if not path:
        return {"error": f"No route found from {from_location} to {to_location}."}
        
    return {
        "id": f"route_{resolved_from.replace(' ', '_')}_{resolved_to.replace(' ', '_')}_{'acc' if accessibility_required else 'std'}",
        "from_location": resolved_from,
        "to_location": resolved_to,
        "path_nodes": path,
        "is_accessible": 1 if accessibility_required else 0
    }

# Tool mapping dict for execution
tool_map = {
    "get_crowd_density": get_crowd_density,
    "get_gate_status": get_gate_status,
    "get_route": get_route
}

# --- Core LLM Orchestrator ---

def query_stadium_assistant(user_message: str, is_staff: bool = False, client=None) -> dict:
    """
    Orchestrates the GenAI response:
    1. Retrieves top-3 RAG documents
    2. Constructs system prompt with context
    3. Runs LLM call with tool definitions (injectable client)
    4. Handles tool execution and generates final response
    """
    rag = get_rag()
    rag_results = rag.retrieve(user_message, top_k=3)
    
    context_str = "\n".join([f"- {doc['title']}: {doc['content']}" for doc in rag_results])
    
    system_prompt = (
        "You are EktaAI, a GenAI stadium operations assistant for the FIFA World Cup 2026.\n"
        "Use the following static stadium facts as context to answer general questions when relevant:\n"
        f"{context_str}\n\n"
    )
    
    if is_staff:
        system_prompt += (
            "You are serving as the operational intelligence portal for STADIUM STAFF.\n"
            "You have access to tools for live digital twin data: get_crowd_density, get_gate_status, get_route.\n"
            "Be precise, professional, alert-oriented, and highlight operational suggestions when needed."
        )
    else:
        system_prompt += (
            "You are serving as the FAN ASSISTANT. Answer user queries helpfully and multilingually (match their language).\n"
            "If they ask for directions or routes, you MUST invoke get_route tool. Always check if they mention 'wheelchair', 'stroller', 'accessible', or 'limited mobility' and set accessibility_required=True.\n"
            "If you generate a route, tell them in your text reply that you have loaded the route map for them."
        )

    llm_res = None
    reply = ""
    tool_calls = []
    tools_list = [get_crowd_density, get_gate_status, get_route]

    # If client is injected, run it directly
    if client is not None:
        logger.info(f"Orchestrator query: using injected client {client.__class__.__name__}")
        try:
            llm_res = client.generate(system_prompt, user_message, tools_list)
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls
        except Exception as e:
            logger.error(f"Injected client failed: {e}. Falling back to default failover.")

    # Core Failover Chain
    # 1. Try Gemini
    if llm_res is None and Config.GEMINI_API_KEY:
        llm_res, success = execute_with_retry_and_circuit_breaker(
            "gemini",
            lambda: GeminiLLMClient(Config.GEMINI_API_KEY),
            system_prompt,
            user_message,
            tools_list
        )
        if success and llm_res:
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls

    # 2. Try Groq
    if llm_res is None and Config.GROQ_API_KEY:
        from backend.app.llm_client import GroqLLMClient
        llm_res, success = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(Config.GROQ_API_KEY),
            system_prompt,
            user_message,
            tools_list
        )
        if success and llm_res:
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls

    # 3. Fallback to Mock Client
    if llm_res is None:
        logger.info("Using MockLLMClient fallback.")
        mock_client = MockLLMClient()
        llm_res = mock_client.generate(system_prompt, user_message, tools_list)
        reply = llm_res.reply
        tool_calls = llm_res.tool_calls

    # Inspect function calls to return structural tool data to the client
    last_tool = None
    route_data = None
    
    for call in tool_calls:
        last_tool = call.name
        args = call.args or {}
        if call.name == "get_route":
            route_res = get_route(
                args.get("from_location", ""),
                args.get("to_location", ""),
                args.get("accessibility_required", False)
            )
            if "error" in route_res:
                route_data = None
                # Inject user-friendly alert inside the assistant response instead of raising ValidationErrors
                reply = f"{reply}\n\n[Error] {route_res['error']}"
            else:
                route_data = route_res
        elif call.name == "get_crowd_density":
            # Execute to trigger side effect or queries if needed
            get_crowd_density(args.get("zone", ""))
        elif call.name == "get_gate_status":
            get_gate_status()

    return {
        "reply": reply,
        "tool_called": last_tool,
        "route": route_data,
        "rag_used": len(rag_results) > 0
    }

