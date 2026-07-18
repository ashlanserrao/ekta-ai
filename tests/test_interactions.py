import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import Config

@pytest.fixture(autouse=True)
def reset_rate_limiters():
    from backend.app.middleware.rate_limit import interaction_limiter, staff_limiter
    interaction_limiter.request_timestamps.clear()
    staff_limiter.request_timestamps.clear()
    yield

def test_log_interaction_requires_no_auth():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/interactions",
            json={"session_id": "test-session-1", "role": "fan", "event_type": "login", "view": None, "meta": {}},
        )
        assert response.status_code == 204

def test_read_interactions_requires_staff_auth():
    with TestClient(app) as client:
        response = client.get("/api/v1/interactions")
        assert response.status_code == 401

def test_read_interactions_returns_logged_event():
    with TestClient(app) as client:
        client.post(
            "/api/v1/interactions",
            json={"session_id": "test-session-2", "role": "fan", "event_type": "page_view", "view": "stats", "meta": {}},
        )

        login_res = client.post("/api/v1/auth/staff/login", json={"passcode": Config.STAFF_PASSCODE})
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/interactions?limit=50", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(e["session_id"] == "test-session-2" for e in data["events"])
        # Never leaks message content or personal fields, only the typed shape above.
        assert all(set(e.keys()) == {"id", "ts", "session_id", "role", "event_type", "view", "meta"} for e in data["events"])

def test_log_interaction_rejects_unknown_event_type():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/interactions",
            json={"session_id": "test-session-3", "role": "fan", "event_type": "not_a_real_type", "view": None, "meta": {}},
        )
        assert response.status_code == 422
