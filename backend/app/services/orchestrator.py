import json
import logging
import re
import time
from backend.app.config import settings
from backend.app.rag import get_rag
from backend.app.llm_client import GeminiLLMClient, MockLLMClient, LLMResult, ToolCall
from backend.app.tools import get_crowd_density, get_gate_status, get_route

logger = logging.getLogger("orchestrator")

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

def execute_with_retry_and_circuit_breaker(provider_name: str, client_initializer, system_prompt: str, user_message: str, tools: list, response_format: dict = None, mode: str = None) -> tuple:
    """
    Executes an LLM call with a safe 2-time retry (3 attempts total) for transient issues, 
    and immediately trips a circuit breaker on daily quota/auth errors, or after consecutive failures.
    Returns: (LLMResult or None, success boolean)
    """
    if provider_name == "gemini" and settings.GEMINI_EXHAUSTED:
        logger.info("Gemini circuit breaker is active. Skipping Gemini.")
        return None, False
    if provider_name == "groq" and settings.GROQ_EXHAUSTED:
        logger.info("Groq circuit breaker is active. Skipping Groq.")
        return None, False
        
    attempts = 3
    backoff = 0.5
    
    for attempt in range(1, attempts + 1):
        try:
            client = client_initializer()
            logger.info(f"[{provider_name.upper()}] Attempt {attempt} of {attempts}...")
            llm_res = client.generate(system_prompt, user_message, tools, response_format=response_format, mode=mode)
            return llm_res, True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{provider_name.upper()}] Attempt {attempt} failed: {error_msg}")
            
            if is_quota_or_rate_limit_error(error_msg):
                logger.warning(f"[{provider_name.upper()}] Quota/Rate Limit/Auth error detected! Tripping circuit breaker immediately.")
                if provider_name == "gemini":
                    settings.GEMINI_EXHAUSTED = True
                elif provider_name == "groq":
                    settings.GROQ_EXHAUSTED = True
                break
                
            if attempt < attempts:
                logger.info(f"Transient error detected. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
                backoff *= 3
            else:
                logger.warning(f"[{provider_name.upper()}] Failed all {attempts} attempts. Tripping circuit breaker for safety.")
                if provider_name == "gemini":
                    settings.GEMINI_EXHAUSTED = True
                elif provider_name == "groq":
                    settings.GROQ_EXHAUSTED = True
                
    return None, False

# Tool mapping dict for execution
tool_map = {
    "get_crowd_density": get_crowd_density,
    "get_gate_status": get_gate_status,
    "get_route": get_route
}

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
    final_provider = "mock"

    # 1. Try Gemini
    if llm_res is None and settings.GEMINI_API_KEY:
        logger.info("Attempting LLM query with Gemini provider.")
        result = execute_with_retry_and_circuit_breaker(
            "gemini",
            lambda: GeminiLLMClient(settings.GEMINI_API_KEY),
            system_prompt,
            user_message,
            tools_list
        )
        if isinstance(result, tuple) and len(result) == 2:
            llm_res, success = result
        else:
            llm_res, success = None, False
            
        if success and llm_res:
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls
            final_provider = "gemini"
        else:
            logger.warning("Gemini failed or rate-limited. Falling back in pipeline.")

    # 2. Try Groq
    if llm_res is None and settings.GROQ_API_KEY:
        logger.info("Attempting LLM query with Groq provider.")
        from backend.app.llm_client import GroqLLMClient
        result = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(settings.GROQ_API_KEY),
            system_prompt,
            user_message,
            tools_list
        )
        if isinstance(result, tuple) and len(result) == 2:
            llm_res, success = result
        else:
            llm_res, success = None, False
            
        if success and llm_res:
            reply = llm_res.reply
            tool_calls = llm_res.tool_calls
            final_provider = "groq"
        else:
            logger.warning("Groq failed or rate-limited. Falling back in pipeline.")

    # 3. Fallback to Mock Client
    if llm_res is None:
        logger.info("Selected LLM provider: Mock client (Fallback)")
        mock_client = MockLLMClient()
        llm_res = mock_client.generate(system_prompt, user_message, tools_list)
        reply = llm_res.reply
        tool_calls = llm_res.tool_calls
        final_provider = "mock"

    logger.info(f"Final LLM execution provider selected: {final_provider}")

    # Inspect function calls to return structural tool data to the client and collect results
    last_tool = None
    route_data = None
    executed_results = []
    
    for call in tool_calls:
        last_tool = call.name
        args = call.args or {}
        result_data = None
        if call.name == "get_route":
            route_res = get_route(
                args.get("from_location", ""),
                args.get("to_location", ""),
                args.get("accessibility_required", False)
            )
            result_data = route_res
            if "error" in route_res:
                route_data = None
                # Inject user-friendly alert inside the assistant response instead of raising ValidationErrors
                reply = f"{reply}\n\n[Error] {route_res['error']}"
            else:
                route_data = route_res
        elif call.name == "get_crowd_density":
            result_data = get_crowd_density(args.get("zone", ""))
        elif call.name == "get_gate_status":
            result_data = get_gate_status()
            
        if result_data:
            executed_results.append((call.name, result_data))

    # If the response has tool calls but the reply content is empty/blank,
    # generate a follow-up LLM response with the executed tool results.
    if not reply.strip() and executed_results:
        tool_results_str = "\n".join([f"Tool '{name}' returned: {json.dumps(res)}" for name, res in executed_results])
        followup_prompt = (
            f"The user's request is: {user_message}\n\n"
            f"Here is the real-time data retrieved from the database to answer their request:\n"
            f"{tool_results_str}\n\n"
            f"Generate a professional, natural-language response based on this data."
        )
        
        logger.info(f"Generating followup LLM response using provider: {final_provider}")
        try:
            if client is not None:
                followup_res = client.generate(system_prompt, followup_prompt, tools=[])
                reply = followup_res.reply
            elif final_provider == "gemini" and settings.GEMINI_API_KEY:
                followup_res = GeminiLLMClient(settings.GEMINI_API_KEY).generate(system_prompt, followup_prompt, tools=[])
                reply = followup_res.reply
            elif final_provider == "groq" and settings.GROQ_API_KEY:
                from backend.app.llm_client import GroqLLMClient
                followup_res = GroqLLMClient(settings.GROQ_API_KEY).generate(system_prompt, followup_prompt, tools=[])
                reply = followup_res.reply
        except Exception as e:
            logger.error(f"Followup LLM response generation failed: {e}")

    # Fallback to direct Python-generated natural-language reply if still empty
    if not reply.strip() and executed_results:
        fallback_parts = []
        for name, res in executed_results:
            if name == "get_crowd_density":
                if "error" in res:
                    fallback_parts.append(f"Unable to retrieve crowd density: {res['error']}")
                else:
                    fallback_parts.append(
                        f"[STAFF OPERATIONAL BRIEF] Zone {res.get('id', 'Unknown')} ({res.get('name', 'Unknown')}) "
                        f"is currently at {int(res.get('density', 0.0)*100)}% capacity ({res.get('current_crowd', 0)} fans)."
                    )
            elif name == "get_gate_status":
                gate_lines = []
                for gate in res:
                    gate_lines.append(f"- {gate['name']}: {gate['status'].upper()} (Congestion: {gate['congestion_level']})")
                fallback_parts.append("Here is the current live status of the stadium gates:\n" + "\n".join(gate_lines))
            elif name == "get_route":
                if "error" in res:
                    fallback_parts.append(f"Routing failed: {res['error']}")
                else:
                    fallback_parts.append(
                        f"Calculated routing path from {res['from_location']} to {res['to_location']}: "
                        f"{' -> '.join(res['path_nodes'])}."
                    )
        reply = "\n\n".join(fallback_parts)

    return {
        "reply": reply,
        "tool_called": last_tool,
        "route": route_data,
        "rag_used": len(rag_results) > 0
    }
