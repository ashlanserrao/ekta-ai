import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.routers.chat import _sanitize_message
from backend.app.services.orchestrator import _looks_like_tool_leak, _sanitize_leak
from backend.app.services import alert_service


def test_security_headers_present_on_api_responses():
    with TestClient(app) as client:
        res = client.get("/")
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert res.headers["X-Frame-Options"] == "DENY"
        assert "max-age" in res.headers["Strict-Transport-Security"]
        assert res.headers["Permissions-Policy"] == "camera=(), geolocation=(), microphone=()"
        assert res.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_csp_relaxed_only_for_interactive_docs():
    with TestClient(app) as client:
        res = client.get("/docs")
        assert res.status_code == 200  # dev environment keeps docs enabled
        assert "Content-Security-Policy" not in res.headers
        # Other security headers still apply to the docs page
        assert res.headers["X-Frame-Options"] == "DENY"


def test_cors_preflight_allows_only_declared_methods():
    origin = settings.ALLOWED_ORIGINS[0]
    with TestClient(app) as client:
        ok = client.options(
            "/api/v1/chat/fan",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert ok.status_code == 200
        allowed = ok.headers["access-control-allow-methods"]
        assert "POST" in allowed and "DELETE" not in allowed

        denied = client.options(
            "/api/v1/chat/fan",
            headers={"Origin": origin, "Access-Control-Request-Method": "DELETE"},
        )
        assert denied.status_code == 400


def test_sanitize_message_rejects_whitespace_only():
    with pytest.raises(HTTPException) as exc:
        _sanitize_message("   ")
    assert exc.value.status_code == 422


def test_sanitize_message_neutralizes_html():
    assert _sanitize_message("<script>alert(1)</script> hi") == "&lt;script&gt;alert(1)&lt;/script&gt; hi"


def test_tool_leak_detection_and_sanitization():
    leaked = 'Sure! get_route({"from_location": "Gate 1", "to_location": "Section 102"})'
    assert _looks_like_tool_leak(leaked)
    assert not _looks_like_tool_leak("The concourse is quiet right now.")
    assert not _looks_like_tool_leak("")

    cleaned = _sanitize_leak(leaked)
    assert "get_route" not in cleaned
    assert "from_location" not in cleaned


def test_alert_cache_is_bounded_lru():
    alert_service._alert_cache.clear()
    limit = alert_service.ALERT_CACHE_MAX_ENTRIES
    for i in range(limit + 25):
        alert_service._cache_put((f"anomaly-{i}",), [{"id": f"anomaly-{i}"}])

    assert len(alert_service._alert_cache) == limit
    # Oldest entries were evicted, newest are retained
    assert alert_service._cache_get(("anomaly-0",)) is None
    assert alert_service._cache_get((f"anomaly-{limit + 24}",)) is not None
    alert_service._alert_cache.clear()
