import json
import pytest

from backend.app.config import settings
from backend.app.services.orchestrator import stream_stadium_assistant, format_tool_brief
from backend.app.mock_llm import MockLLMClient


class _AlwaysFailsClient:
    """Simulates a Groq client whose API key/quota has been exhausted: every
    call raises, exactly like a 429 from a rate-limited Groq account."""
    provider_name = "groq"

    def generate(self, *args, **kwargs):
        raise RuntimeError("429 Too Many Requests: rate limit exceeded")

    def generate_stream(self, *args, **kwargs):
        raise RuntimeError("429 Too Many Requests: rate limit exceeded")


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    settings.set_exhausted("groq", False)
    yield
    settings.set_exhausted("groq", False)


def _collect(gen):
    return [json.loads(chunk) for chunk in gen]


def test_stream_falls_back_to_mock_when_groq_client_raises():
    """When the injected 'groq' client fails outright (e.g. quota exhausted),
    the SSE stream must still complete with mock-provider tokens instead of
    raising and aborting the connection (the reported "network error" bug)."""
    chunks = _collect(stream_stadium_assistant(
        "Where is the lost and found office?",
        is_staff=False,
        client=_AlwaysFailsClient(),
    ))
    assert chunks, "stream produced no output"
    assert all(c["provider"] == "mock" for c in chunks)
    assert "".join(c["token"] for c in chunks).strip()


def test_stream_routing_query_falls_back_and_still_returns_dijkstra_route():
    """A routing query should still resolve a real Dijkstra path via the mock
    fallback even when the primary (Groq) client is broken."""
    chunks = _collect(stream_stadium_assistant(
        "How do I get from Gate 2 to Section 204?",
        is_staff=False,
        client=_AlwaysFailsClient(),
    ))
    routed = [c for c in chunks if c.get("route")]
    assert routed, "no chunk carried a route"
    route = routed[0]["route"]
    assert route["from_location"] == "Gate 2"
    assert route["to_location"] == "Section 204 Entry"
    assert len(route["path_nodes"]) >= 2


def test_stream_mock_mode_returns_real_dijkstra_route():
    """Mock mode (no Groq at all) must detect routing intent and resolve an
    actual Dijkstra path over the routing graph, not a canned response."""
    chunks = _collect(stream_stadium_assistant(
        "How do I get from Gate 1 to Section 305?",
        is_staff=False,
        client=MockLLMClient(),
    ))
    routed = [c for c in chunks if c.get("route")]
    assert routed, "no chunk carried a route"
    route = routed[0]["route"]
    assert "error" not in route
    assert route["path_nodes"][0] == "Gate 1"
    assert route["path_nodes"][-1] == "Section 305 Entry"
    assert len(route["path_nodes"]) >= 2


def test_stream_survives_unexpected_failure_outside_llm_calls(monkeypatch):
    """Any unexpected failure outside the known LLM-failure paths (e.g. the RAG
    lookup itself) must still degrade to a chat message, not kill the SSE stream."""
    import backend.app.services.orchestrator as orch

    class _BrokenRag:
        def retrieve(self, *args, **kwargs):
            raise RuntimeError("simulated RAG failure")

    monkeypatch.setattr(orch, "get_rag", lambda: _BrokenRag())

    chunks = _collect(stream_stadium_assistant("ping", is_staff=False))
    assert chunks, "stream produced no output on unexpected failure"
    assert "".join(c["token"] for c in chunks).strip()


def test_format_tool_brief_handles_gate_status_tool_error():
    """format_tool_brief must not crash when get_gate_status itself failed and
    returned an {'error': ...} dict instead of a list of gates (this previously
    raised TypeError uncaught inside the SSE generator)."""
    brief = format_tool_brief([("get_gate_status", {"error": "database locked"})])
    assert "database locked" in brief
