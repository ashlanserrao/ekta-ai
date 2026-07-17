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
        "credentials",
        "403",
        "forbidden"
    ])

def execute_with_retry_and_circuit_breaker(provider_name: str, client_initializer, system_prompt: str, user_message: str, tools: list, response_format: dict = None, mode: str = None, history: list = None) -> tuple:
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
            llm_res = client.generate(system_prompt, user_message, tools, response_format=response_format, mode=mode, history=history)
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

_TOOL_LEAK_RE = re.compile(
    r'(get_crowd_density|get_gate_status|get_route|<function|function=|'
    r'\{\s*"(zone|from_location|to_location|accessibility_required)")',
    re.IGNORECASE,
)


def _looks_like_tool_leak(text: str) -> bool:
    """True if the model printed a tool call as prose text instead of calling it."""
    return bool(text) and bool(_TOOL_LEAK_RE.search(text))


def _sanitize_leak(text: str) -> str:
    """Strip leaked tool-call fragments (JSON blobs, function syntax) from a reply."""
    if not text:
        return ""
    text = re.sub(r'\{[^{}]*\}', '', text)
    text = re.sub(r'<function[^>]*>', '', text)
    text = re.sub(r'(get_crowd_density|get_gate_status|get_route)\s*\([^)]*\)', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def format_tool_brief(executed_results: list) -> str:
    """Deterministically render executed tool results into a plain-language brief.
    Used as the fast-path for staff queries (no second LLM round-trip) and as the
    universal fallback when an LLM followup produces no text."""
    parts = []
    for name, res in executed_results:
        if name == "get_crowd_density":
            if "error" in res:
                parts.append(f"Unable to retrieve crowd density: {res['error']}")
            else:
                parts.append(
                    f"Live crowd density in {res['name']} ({res.get('type', 'zone')}) is {round(res['density']*100)}% "
                    f"({res['current_crowd']} occupants out of {res['capacity']} capacity)."
                )
        elif name == "get_gate_status":
            if "error" in res:
                parts.append(f"Unable to retrieve gate status: {res['error']}")
            else:
                gate_lines = [
                    f"- {gate['name']}: {gate['status'].upper()} (Congestion: {gate['congestion_level']})"
                    for gate in res
                ]
                parts.append("Here is the current live status of the stadium gates:\n" + "\n".join(gate_lines))
        elif name == "get_route":
            if "error" in res:
                parts.append(f"Routing failed: {res['error']}")
            else:
                parts.append(
                    f"Calculated routing path from {res['from_location']} to {res['to_location']}: "
                    f"{' -> '.join(res['path_nodes'])}."
                )
    return "\n\n".join(parts)

def build_system_prompt(rag_results: list, is_staff: bool) -> str:
    """Construct the assistant system prompt with RAG context.

    Note: we deliberately do NOT tell the model 'never print tool calls'. That
    instruction is counterproductive — it makes the model narrate the call as prose
    instead of emitting a structured tool call. Tool execution is handled server-side
    and only clean output is streamed, so the warning is unnecessary and harmful.
    """
    context_str = "\n".join([f"- {doc['title']}: {doc['content']}" for doc in rag_results])

    prompt = (
        "You are EktaAI, a GenAI stadium operations assistant for the FIFA World Cup 2026.\n"
        "Use the following static stadium facts as context to answer general questions when relevant:\n"
        f"{context_str}\n\n"
    )

    if is_staff:
        prompt += (
            "You are the operational intelligence portal for STADIUM STAFF. Use your live-data tools "
            "(get_crowd_density, get_gate_status, get_route) whenever the user asks about crowd levels, "
            "gate status, or routing. Be precise, professional, and alert-oriented."
        )
    else:
        prompt += (
            "You are the FAN ASSISTANT. Answer helpfully and in the user's own language (match it).\n"
            "Only call get_route when the user gives BOTH a starting point (e.g., Gate 1, Gate 2, Gate 3, Gate 4) "
            "and a destination section (e.g., Section 102, Section 105, Section 204, Section 305). If they only ask "
            "where something is, answer from the facts without routing. When a route is generated, tell them you have "
            "loaded the route map for them."
        )

    prompt += (
        "\nKeep responses concise and actionable — under 3-4 sentences, optimized for on-the-go reading."
    )
    return prompt

def query_stadium_assistant(user_message: str, is_staff: bool = False, client=None, history: list = None) -> dict:
    """
    Orchestrates the GenAI response:
    1. Retrieves top-3 RAG documents
    2. Constructs system prompt with context
    3. Runs LLM call with tool definitions (injectable client)
    4. Handles tool execution and generates final response
    """
    rag = get_rag()
    rag_results = rag.retrieve(user_message, top_k=3)
    
    system_prompt = build_system_prompt(rag_results, is_staff)
 
    llm_res = None
    reply = ""
    tool_calls = []
    tools_list = [get_crowd_density, get_gate_status, get_route]

    # If client is injected, run it directly
    if client is not None:
        logger.info(f"Orchestrator query: using injected client {client.__class__.__name__}")
        try:
            llm_res = client.generate(system_prompt, user_message, tools_list, history=history)
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
            tools_list,
            history=history
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
        llm_res = mock_client.generate(system_prompt, user_message, tools_list, history=history)
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

    # For STAFF tool queries, skip the second LLM round-trip: staff want precise
    # numbers, and the deterministic brief is instant (cuts latency ~50%).
    # Fans keep the LLM followup so replies stay natural and language-matched.
    if executed_results and is_staff:
        reply = format_tool_brief(executed_results)
    elif executed_results and final_provider != "mock":
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
                followup_res = client.generate(system_prompt, followup_prompt, tools=[], history=history)
                reply = followup_res.reply
            elif final_provider == "groq" and settings.GROQ_API_KEY:
                from backend.app.llm_client import GroqLLMClient
                followup_res = GroqLLMClient(settings.GROQ_API_KEY).generate(system_prompt, followup_prompt, tools=[], history=history)
                reply = followup_res.reply
        except Exception as e:
            logger.error(f"Followup LLM response generation failed: {e}")

    # Fallback to direct Python-generated natural-language reply if still empty
    if not reply.strip() and executed_results:
        reply = format_tool_brief(executed_results)

    last_tool = tool_calls[0].name if tool_calls else None

    return {
        "reply": reply,
        "tool_called": last_tool,
        "route": route_data,
        "rag_used": len(rag_results) > 0,
        "provider": final_provider
    }

def stream_stadium_assistant(user_message: str, is_staff: bool = False, client=None, history: list = None):
    """
    Generator yielding Server-Sent Events (SSE) compatible JSON strings for chat streaming.

    Once the SSE response has started, an uncaught exception can no longer be turned
    into a clean HTTP error — the ASGI server just aborts the connection, which the
    browser surfaces as a raw network error instead of a chat message. The inner
    generator already degrades to MockLLMClient on known LLM failures; this wrapper
    is the last-resort net for anything else (e.g. RAG lookup or tool-result
    formatting failures) so the user always gets a message, never a dead connection.
    """
    try:
        yield from _stream_stadium_assistant_inner(user_message, is_staff, client, history)
    except Exception as e:
        logger.error(f"Unhandled error in stream_stadium_assistant: {e}")
        fallback = "I'm having trouble processing that right now. Please try again in a moment."
        for word in fallback.split(" "):
            yield json.dumps({
                "token": word + " ",
                "provider": "mock",
                "tool_called": None,
                "route": None
            })


def _stream_stadium_assistant_inner(user_message: str, is_staff: bool = False, client=None, history: list = None):
    rag = get_rag()
    rag_results = rag.retrieve(user_message, top_k=3)
    
    system_prompt = build_system_prompt(rag_results, is_staff)

    # Determine provider and client
    final_provider = "mock"
    client_instance = None

    if client is not None:
        client_instance = client
        final_provider = getattr(client, "provider_name", "mock")
    elif settings.GROQ_API_KEY and not settings.is_exhausted("groq"):
        from backend.app.llm_client import GroqLLMClient
        client_instance = GroqLLMClient(settings.GROQ_API_KEY)
        final_provider = "groq"
    else:
        client_instance = MockLLMClient()
        final_provider = "mock"

    tools_list = [get_crowd_density, get_gate_status, get_route]

    # First pass is NON-streaming: models emit reliable *structured* tool calls this
    # way. Streamed tool-calls are flaky (llama can leak the raw call as prose text),
    # so we decide tools here, then stream only the final answer below.
    reply = ""
    tool_calls = []
    try:
        first = client_instance.generate(system_prompt, user_message, tools_list, history=history)
        reply = first.reply or ""
        tool_calls = first.tool_calls or []
    except Exception as e:
        logger.error(f"{final_provider} generate failed: {e}. Falling back to Mock.")
        if final_provider == "groq":
            settings.set_exhausted("groq", True)
        final_provider = "mock"
        client_instance = MockLLMClient()
        try:
            first = client_instance.generate(system_prompt, user_message, tools_list, history=history)
            reply = first.reply or ""
            tool_calls = first.tool_calls or []
        except Exception as e2:
            logger.error(f"Mock generate failed: {e2}")
            reply = "I'm sorry, I'm having trouble processing that right now. Please try again."

    # Occasionally a model prints a tool call as prose instead of emitting a
    # structured call. Retry once (usually resolves it); if it still leaks, sanitize.
    if not tool_calls and _looks_like_tool_leak(reply):
        logger.info("Detected leaked tool-call text; retrying decision pass once.")
        try:
            retry = client_instance.generate(system_prompt, user_message, tools_list, history=history)
            if retry.tool_calls:
                tool_calls = retry.tool_calls
                reply = retry.reply or ""
            else:
                reply = _sanitize_leak(retry.reply or reply)
        except Exception as e:
            logger.error(f"Tool-leak retry failed: {e}")
            if final_provider == "groq":
                settings.set_exhausted("groq", True)
            reply = _sanitize_leak(reply)

    # No tool calls: stream the (already generated) direct answer word by word.
    if not tool_calls:
        if not reply.strip():
            reply = "I'm here to help with stadium navigation, facilities, and accessibility. Could you rephrase your question?"
        for word in reply.split(" "):
            yield json.dumps({
                "token": word + " ",
                "provider": final_provider,
                "tool_called": None,
                "route": None
            })
        return

    # Tool calls were made: execute them, then stream the answer.
    last_tool = tool_calls[0].name
    executed_results = []
    for tool in tool_calls:
        if tool.name in tool_map:
            try:
                result_data = tool_map[tool.name](**tool.args)
                executed_results.append((tool.name, result_data))
            except Exception as e:
                executed_results.append((tool.name, {"error": str(e)}))

    route_data = None
    for name, res in executed_results:
        if name == "get_route":
            route_data = res

    followup_reply_sent = False

    # STAFF fast-path: stream the deterministic brief and skip the second LLM
    # round-trip (~50% lower latency). Fans get an LLM followup for natural,
    # language-matched prose.
    if not is_staff:
        tool_results_str = "\n".join([f"Tool {name} output: {json.dumps(res)}" for name, res in executed_results])
        followup_prompt = (
            f"The user's request is: {user_message}\n\n"
            f"Here is the real-time data retrieved from the database to answer their request:\n"
            f"{tool_results_str}\n\n"
            f"Generate a professional, natural-language response based on this data."
        )
        try:
            followup_stream = client_instance.generate_stream(system_prompt, followup_prompt, tools=[], history=history)
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

    # Staff, or a fan followup that produced nothing: stream the deterministic brief.
    if not followup_reply_sent:
        brief = format_tool_brief(executed_results)
        for word in brief.split(" "):
            yield json.dumps({
                "token": word + " ",
                "provider": final_provider,
                "tool_called": last_tool,
                "route": route_data
            })
