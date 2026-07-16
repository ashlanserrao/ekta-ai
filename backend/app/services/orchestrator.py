import json
import logging
import re
import time
from backend.app.config import settings
from backend.app.rag import get_rag
from backend.app.llm_client import MockLLMClient, LLMResult, ToolCall
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
    if settings.is_exhausted(provider_name):
        logger.info(f"{provider_name.capitalize()} circuit breaker is active. Skipping {provider_name.capitalize()}.")
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
                settings.set_exhausted(provider_name, True)
                break
                
            if attempt < attempts:
                logger.info(f"Transient error detected. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
                backoff *= 3
            else:
                logger.warning(f"[{provider_name.upper()}] Failed all {attempts} attempts. Tripping circuit breaker for safety.")
                settings.set_exhausted(provider_name, True)
                
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

    # Optimization #3: Enforce strict brevity in instructions
    concise_instruction = (
        "\nIMPORTANT: Your response must be extremely concise, direct, and actionable. "
        "Keep your answers brief and under 3-4 sentences, optimized for rapid on-the-go reading.\n"
    )
    system_prompt += concise_instruction
 
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

    # 1. Try Groq
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

    # 2. Fallback to Mock Client
    if llm_res is None:
        logger.info("Selected LLM provider: Mock client (Fallback)")
        mock_client = MockLLMClient()
        llm_res = mock_client.generate(system_prompt, user_message, tools_list)
        reply = llm_res.reply
        tool_calls = llm_res.tool_calls
        final_provider = "mock"

    logger.info(f"Final LLM execution provider selected: {final_provider}")

    # Handle Tool Calls
    executed_results = []
    if tool_calls:
        logger.info(f"LLM generated tool calls: {tool_calls}")
        for tool in tool_calls:
            if tool.name in tool_map:
                try:
                    logger.info(f"Executing tool {tool.name} with args {tool.args}")
                    result_data = tool_map[tool.name](**tool.args)
                    executed_results.append((tool.name, result_data))
                except Exception as e:
                    logger.error(f"Tool execution for {tool.name} failed: {e}")
                    executed_results.append((tool.name, {"error": str(e)}))

    # Route extraction mapping for Fan Assistant map rendering
    route_data = None
    if executed_results:
        for name, res in executed_results:
            if name == "get_route":
                route_data = res

    # Generate followup natural-language reply if tools were executed
    if executed_results and final_provider != "mock":
        tool_results_str = "\n".join([f"Tool {name} output: {json.dumps(res)}" for name, res in executed_results])
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
                        f"Live crowd density in {res['name']} ({res['type']}) is {Math.round(res['density']*100)}% "
                        f"({res['current_crowd']} occupants out of {res['capacity']} capacity)."
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

    last_tool = tool_calls[0].name if tool_calls else None

    return {
        "reply": reply,
        "tool_called": last_tool,
        "route": route_data,
        "rag_used": len(rag_results) > 0,
        "provider": final_provider
    }

def stream_stadium_assistant(user_message: str, is_staff: bool = False, client=None):
    """
    Generator yielding Server-Sent Events (SSE) compatible JSON strings for chat streaming.
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

    # Optimization #3: Enforce strict brevity in instructions
    concise_instruction = (
        "\nIMPORTANT: Your response must be extremely concise, direct, and actionable. "
        "Keep your answers brief and under 3-4 sentences, optimized for rapid on-the-go reading.\n"
    )
    system_prompt += concise_instruction

    # Determine provider and client
    final_provider = "mock"
    client_instance = None

    if client is not None:
        client_instance = client
        final_provider = client.__class__.__name__.lower().replace("llmclient", "")
    elif settings.GROQ_API_KEY and not settings.is_exhausted("groq"):
        from backend.app.llm_client import GroqLLMClient
        client_instance = GroqLLMClient(settings.GROQ_API_KEY)
        final_provider = "groq"
    else:
        client_instance = MockLLMClient()
        final_provider = "mock"

    tools_list = [get_crowd_density, get_gate_status, get_route]
    
    tool_calls_map = {}
    text_content = []
    
    # Try streaming from primary model
    try:
        stream = client_instance.generate_stream(system_prompt, user_message, tools_list)
        for delta in stream:
            # Check for tool calls delta
            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    idx = tc.get("index", 0)
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {"name": "", "args_str": ""}
                    
                    func = tc.get("function", {})
                    if func.get("name"):
                        tool_calls_map[idx]["name"] += func["name"]
                    if func.get("arguments"):
                        tool_calls_map[idx]["args_str"] += func["arguments"]
            
            # Check for content delta
            if "content" in delta and delta["content"]:
                text_content.append(delta["content"])
                yield json.dumps({
                    "token": delta["content"],
                    "provider": final_provider,
                    "tool_called": None,
                    "route": None
                })
    except Exception as e:
        logger.error(f"{final_provider} stream failed: {e}. Falling back to Mock.")
        if final_provider == "groq":
            settings.set_exhausted("groq", True)
            final_provider = "mock"
            client_instance = MockLLMClient()
            stream = client_instance.generate_stream(system_prompt, user_message, tools_list)
            for delta in stream:
                if "content" in delta and delta["content"]:
                    yield json.dumps({
                        "token": delta["content"],
                        "provider": final_provider,
                        "tool_called": None,
                        "route": None
                    })
            return

    # Parse any accumulated tool calls
    tool_calls = []
    for idx, tc_data in tool_calls_map.items():
        name = tc_data["name"]
        args_str = tc_data["args_str"]
        try:
            args = json.loads(args_str) if args_str else {}
        except Exception:
            args = {}
        tool_calls.append(ToolCall(name=name, args=args))

    # If tool calls were made:
    if tool_calls:
        last_tool = tool_calls[0].name
        
        # Execute tool calls
        executed_results = []
        for tool in tool_calls:
            if tool.name in tool_map:
                try:
                    result_data = tool_map[tool.name](**tool.args)
                    executed_results.append((tool.name, result_data))
                except Exception as e:
                    executed_results.append((tool.name, {"error": str(e)}))

        # Check for route data to send
        route_data = None
        for name, res in executed_results:
            if name == "get_route":
                route_data = res

        # Run followup query (streaming)
        tool_results_str = "\n".join([f"Tool {name} output: {json.dumps(res)}" for name, res in executed_results])
        followup_prompt = (
            f"The user's request is: {user_message}\n\n"
            f"Here is the real-time data retrieved from the database to answer their request:\n"
            f"{tool_results_str}\n\n"
            f"Generate a professional, natural-language response based on this data."
        )

        followup_reply_sent = False
        try:
            followup_stream = client_instance.generate_stream(system_prompt, followup_prompt, tools=[])
            for delta in followup_stream:
                if "content" in delta and delta["content"]:
                    followup_reply_sent = True
                    yield json.dumps({
                        "token": delta["content"],
                        "provider": final_provider,
                        "tool_called": last_tool,
                        "route": route_data
                    })
        except Exception as e:
            logger.error(f"Followup stream failed: {e}")
            
        # Fallback to direct Python-generated natural-language reply if still empty
        if not followup_reply_sent:
            fallback_parts = []
            for name, res in executed_results:
                if name == "get_crowd_density":
                    if "error" in res:
                        fallback_parts.append(f"Unable to retrieve crowd density: {res['error']}")
                    else:
                        fallback_parts.append(
                            f"Live crowd density in {res['name']} ({res['type']}) is {Math.round(res['density']*100)}% "
                            f"({res['current_crowd']} occupants out of {res['capacity']} capacity)."
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
            # Yield full reply as single tokens or chunks
            for word in reply.split(" "):
                yield json.dumps({
                    "token": word + " ",
                    "provider": final_provider,
                    "tool_called": last_tool,
                    "route": route_data
                })
