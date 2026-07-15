import os
import json
import logging
import re
from backend.app.config import Config
from backend.app.database import get_db_connection
from backend.app.rag import get_rag

logger = logging.getLogger("llm")

from backend.app.llm_client import GeminiLLMClient, MockLLMClient, ToolCall, LLMResult

# --- Define Python Tool Functions ---

def get_crowd_density(zone: str) -> dict:
    """
    Gets the current crowd density and capacity information for a specific stadium zone or concourse.
    :param zone: The zone ID (e.g. 'Zone-A', 'Zone-B', 'Zone-C') or zone name.
    """
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

def get_gate_status() -> list:
    """
    Gets the status (open/closed) and congestion level of all stadium gates.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, status, congestion_level, zone_id FROM gates")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_route(from_location: str, to_location: str, accessibility_required: bool = False) -> dict:
    """
    Retrieves the routing path between two locations, filtering for wheelchair accessibility if required.
    :param from_location: Start point (e.g., 'Gate 1', 'Gate 2')
    :param to_location: Destination point (e.g., 'Section 102', 'Section 204')
    :param accessibility_required: True if step-free accessible route is needed.
    """
    from backend.app.routing import find_path
    
    def resolve_node_name(query: str) -> str:
        q_lower = query.lower().strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM nodes")
        nodes = [r["id"] for r in cursor.fetchall()]
        conn.close()
        
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
    
    path = find_path(resolved_from, resolved_to, accessibility_required)
    
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
        try:
            logger.info("Attempting live Gemini query...")
            client_instance = GeminiLLMClient(Config.GEMINI_API_KEY)
            llm_res = client_instance.generate(system_prompt, user_message, tools_list)
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls
            logger.info("Gemini response generated successfully.")
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}. Switching to Groq fallback.")

    # 2. Try Groq
    if llm_res is None and Config.GROQ_API_KEY:
        try:
            logger.info("Attempting live Groq query...")
            from backend.app.llm_client import GroqLLMClient
            client_instance = GroqLLMClient(Config.GROQ_API_KEY)
            llm_res = client_instance.generate(system_prompt, user_message, tools_list)
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls
            logger.info("Groq response generated successfully.")
        except Exception as e:
            logger.error(f"Groq generation failed: {e}. Switching to Mock client fallback.")

    # 3. Fallback to Mock Client
    if llm_res is None:
        logger.info("Using MockLLMClient fallback.")
        client_instance = MockLLMClient()
        llm_res = client_instance.generate(system_prompt, user_message, tools_list)
        reply = llm_res.reply
        tool_calls = llm_res.tool_calls

    # Inspect function calls to return structural tool data to the client
    last_tool = None
    route_data = None
    
    for call in tool_calls:
        last_tool = call.name
        if call.name == "get_route":
            route_data = get_route(
                call.args.get("from_location", ""),
                call.args.get("to_location", ""),
                call.args.get("accessibility_required", False)
            )
        elif call.name == "get_crowd_density":
            # Execute to trigger side effect or queries if needed
            get_crowd_density(call.args.get("zone", ""))
        elif call.name == "get_gate_status":
            get_gate_status()

    return {
        "reply": reply,
        "tool_called": last_tool,
        "route": route_data,
        "rag_used": len(rag_results) > 0
    }

