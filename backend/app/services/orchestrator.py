"""GenAI orchestration for the fan and staff chat assistants.

Flow: retrieve RAG context -> pick a provider (injected client, Groq, or the
offline mock) -> let the model decide tool calls -> execute tools against the
digital twin -> render the final reply (LLM followup for fans, deterministic
brief for staff). Every path degrades gracefully: retries + a circuit breaker
guard the Groq calls, and the mock client keeps the app fully functional offline.
"""
import json
import logging
import re
import time
from typing import Callable, Iterator, List, Optional, Tuple

from backend.app.config import settings
from backend.app.llm_client import GroqLLMClient, LLMResult, ToolCall
from backend.app.mock_llm import MockLLMClient
from backend.app.rag import get_rag
from backend.app.tools import get_crowd_density, get_gate_status, get_route

logger = logging.getLogger("orchestrator")

RETRY_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 0.5
BACKOFF_MULTIPLIER = 3

TOOL_REGISTRY = {
    "get_crowd_density": get_crowd_density,
    "get_gate_status": get_gate_status,
    "get_route": get_route,
}

# Signature of a model printing a tool call as prose instead of invoking it.
_TOOL_LEAK_RE = re.compile(
    r'(get_crowd_density|get_gate_status|get_route|<function|function=|'
    r'\{\s*"(zone|from_location|to_location|accessibility_required)")',
    re.IGNORECASE,
)

QUOTA_ERROR_MARKERS = (
    "quota", "exhausted", "limit", "429", "too many requests", "resource_exhausted",
    "billing", "api key", "invalid key", "unauthorized", "auth", "credentials",
    "403", "forbidden",
)


def is_quota_or_rate_limit_error(error_msg: str) -> bool:
    """Detect quota exhaustion, rate limits, or auth errors (non-retryable)."""
    error_lower = error_msg.lower()
    return any(marker in error_lower for marker in QUOTA_ERROR_MARKERS)


def execute_with_retry_and_circuit_breaker(
    provider_name: str,
    client_initializer: Callable,
    system_prompt: str,
    user_message: str,
    tools: Optional[list],
    response_format: Optional[dict] = None,
    mode: Optional[str] = None,
    history: Optional[list] = None,
) -> Tuple[Optional[LLMResult], bool]:
    """Run an LLM call with retries for transient errors and a circuit breaker.

    Quota/auth errors trip the breaker immediately; transient errors are retried
    with exponential backoff, tripping the breaker only after all attempts fail.
    Returns (LLMResult or None, success flag).
    """
    if settings.is_exhausted(provider_name):
        logger.info(f"{provider_name.capitalize()} circuit breaker is active. Skipping.")
        return None, False

    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            client = client_initializer()
            logger.info(f"[{provider_name.upper()}] Attempt {attempt} of {RETRY_ATTEMPTS}...")
            llm_res = client.generate(
                system_prompt, user_message, tools,
                response_format=response_format, mode=mode, history=history,
            )
            return llm_res, True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{provider_name.upper()}] Attempt {attempt} failed: {error_msg}")

            if is_quota_or_rate_limit_error(error_msg):
                logger.warning(f"[{provider_name.upper()}] Quota/auth error — tripping circuit breaker immediately.")
                settings.set_exhausted(provider_name, True)
                break

            if attempt < RETRY_ATTEMPTS:
                logger.info(f"Transient error. Sleeping {backoff}s before retry...")
                time.sleep(backoff)
                backoff *= BACKOFF_MULTIPLIER
            else:
                logger.warning(f"[{provider_name.upper()}] Failed all {RETRY_ATTEMPTS} attempts. Tripping circuit breaker.")
                settings.set_exhausted(provider_name, True)

    return None, False


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


def format_tool_brief(executed_results: List[Tuple[str, object]]) -> str:
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


def _execute_tools(tool_calls: List[ToolCall]) -> List[Tuple[str, object]]:
    """Run each requested tool against the twin; failures become error payloads."""
    executed = []
    for tool in tool_calls:
        if tool.name not in TOOL_REGISTRY:
            continue
        try:
            logger.info(f"Executing tool {tool.name} with args {tool.args}")
            executed.append((tool.name, TOOL_REGISTRY[tool.name](**tool.args)))
        except Exception as e:
            logger.error(f"Tool execution for {tool.name} failed: {e}")
            executed.append((tool.name, {"error": str(e)}))
    return executed


def _extract_route(executed_results: List[Tuple[str, object]]) -> Optional[dict]:
    """Pull the last get_route result so the frontend can render it on the map."""
    route_data = None
    for name, res in executed_results:
        if name == "get_route":
            route_data = res
    return route_data


def _build_followup_prompt(user_message: str, executed_results: List[Tuple[str, object]]) -> str:
    tool_results_str = "\n".join(
        f"Tool {name} output: {json.dumps(res)}" for name, res in executed_results
    )
    return (
        f"The user's request is: {user_message}\n\n"
        f"Here is the real-time data retrieved from the database to answer their request:\n"
        f"{tool_results_str}\n\n"
        f"Generate a professional, natural-language response based on this data."
    )


def _tools_list() -> list:
    return [get_crowd_density, get_gate_status, get_route]


def query_stadium_assistant(
    user_message: str,
    is_staff: bool = False,
    client=None,
    history: Optional[list] = None,
) -> dict:
    """
    Orchestrates the GenAI response:
    1. Retrieves top-3 RAG documents
    2. Constructs system prompt with context
    3. Runs LLM call with tool definitions (injectable client)
    4. Handles tool execution and generates final response
    """
    rag_results = get_rag().retrieve(user_message, top_k=3)
    system_prompt = build_system_prompt(rag_results, is_staff)
    tools_list = _tools_list()

    llm_res: Optional[LLMResult] = None
    final_provider = "mock"

    # 1. Injected client (tests / previews) runs first.
    if client is not None:
        logger.info(f"Orchestrator query: using injected client {client.__class__.__name__}")
        try:
            llm_res = client.generate(system_prompt, user_message, tools_list, history=history)
        except Exception as e:
            logger.error(f"Injected client failed: {e}. Falling back to default failover.")

    # 2. Groq, guarded by retry + circuit breaker.
    if llm_res is None and settings.GROQ_API_KEY:
        logger.info("Attempting LLM query with Groq provider.")
        llm_res, success = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(settings.GROQ_API_KEY),
            system_prompt,
            user_message,
            tools_list,
            history=history,
        )
        if success and llm_res:
            final_provider = "groq"
        else:
            llm_res = None
            logger.warning("Groq failed or rate-limited. Falling back in pipeline.")

    # 3. Offline mock keeps the assistant available with no key / no network.
    if llm_res is None:
        logger.info("Selected LLM provider: Mock client (Fallback)")
        llm_res = MockLLMClient().generate(system_prompt, user_message, tools_list, history=history)
        final_provider = "mock"

    logger.info(f"Final LLM execution provider selected: {final_provider}")
    reply = llm_res.reply
    tool_calls = llm_res.tool_calls

    executed_results = _execute_tools(tool_calls) if tool_calls else []
    route_data = _extract_route(executed_results)

    # For STAFF tool queries, skip the second LLM round-trip: staff want precise
    # numbers, and the deterministic brief is instant (cuts latency ~50%).
    # Fans keep the LLM followup so replies stay natural and language-matched.
    if executed_results and is_staff:
        reply = format_tool_brief(executed_results)
    elif executed_results and final_provider != "mock":
        followup_prompt = _build_followup_prompt(user_message, executed_results)
        logger.info(f"Generating followup LLM response using provider: {final_provider}")
        try:
            if client is not None:
                reply = client.generate(system_prompt, followup_prompt, tools=[], history=history).reply
            elif final_provider == "groq" and settings.GROQ_API_KEY:
                reply = GroqLLMClient(settings.GROQ_API_KEY).generate(
                    system_prompt, followup_prompt, tools=[], history=history
                ).reply
        except Exception as e:
            logger.error(f"Followup LLM response generation failed: {e}")

    # Fallback to the deterministic brief if the followup produced no text.
    if not reply.strip() and executed_results:
        reply = format_tool_brief(executed_results)

    return {
        "reply": reply,
        "tool_called": tool_calls[0].name if tool_calls else None,
        "route": route_data,
        "rag_used": len(rag_results) > 0,
        "provider": final_provider,
    }


def _sse_token(token: str, provider: str, tool_called: Optional[str], route: Optional[dict]) -> str:
    return json.dumps({
        "token": token,
        "provider": provider,
        "tool_called": tool_called,
        "route": route,
    })


def _stream_words(text: str, provider: str, tool_called: Optional[str] = None,
                  route: Optional[dict] = None) -> Iterator[str]:
    """Stream a pre-computed reply word by word as SSE JSON payloads."""
    for word in text.split(" "):
        yield _sse_token(word + " ", provider, tool_called, route)


def stream_stadium_assistant(
    user_message: str,
    is_staff: bool = False,
    client=None,
    history: Optional[list] = None,
) -> Iterator[str]:
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
        yield from _stream_words(fallback, "mock")


def _select_stream_client(client) -> Tuple[object, str]:
    """Pick the provider for a streaming turn: injected client, Groq, or mock."""
    if client is not None:
        return client, getattr(client, "provider_name", "mock")
    if settings.GROQ_API_KEY and not settings.is_exhausted("groq"):
        return GroqLLMClient(settings.GROQ_API_KEY), "groq"
    return MockLLMClient(), "mock"


def _stream_stadium_assistant_inner(
    user_message: str,
    is_staff: bool = False,
    client=None,
    history: Optional[list] = None,
) -> Iterator[str]:
    rag_results = get_rag().retrieve(user_message, top_k=3)
    system_prompt = build_system_prompt(rag_results, is_staff)
    client_instance, final_provider = _select_stream_client(client)
    tools_list = _tools_list()

    # First pass is NON-streaming: models emit reliable *structured* tool calls this
    # way. Streamed tool-calls are flaky (llama can leak the raw call as prose text),
    # so we decide tools here, then stream only the final answer below.
    reply = ""
    tool_calls: List[ToolCall] = []
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
        yield from _stream_words(reply, final_provider)
        return

    # Tool calls were made: execute them, then stream the answer.
    last_tool = tool_calls[0].name
    executed_results = _execute_tools(tool_calls)
    route_data = _extract_route(executed_results)

    followup_reply_sent = False

    # STAFF fast-path: stream the deterministic brief and skip the second LLM
    # round-trip (~50% lower latency). Fans get an LLM followup for natural,
    # language-matched prose.
    if not is_staff:
        followup_prompt = _build_followup_prompt(user_message, executed_results)
        try:
            followup_stream = client_instance.generate_stream(system_prompt, followup_prompt, tools=[], history=history)
            for delta in followup_stream:
                if delta.get("content"):
                    followup_reply_sent = True
                    yield _sse_token(delta["content"], final_provider, last_tool, route_data)
        except Exception as e:
            logger.error(f"Followup stream failed: {e}")

    # Staff, or a fan followup that produced nothing: stream the deterministic brief.
    if not followup_reply_sent:
        brief = format_tool_brief(executed_results)
        yield from _stream_words(brief, final_provider, last_tool, route_data)
