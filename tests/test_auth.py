import pytest
import jwt
import datetime
import hmac
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.middleware.rate_limit import staff_limiter
from backend.app.config import settings

@pytest.fixture(autouse=True)
def reset_rate_limiters():
    staff_limiter.request_timestamps.clear()
    yield

def test_login_success():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/staff/login",
            json={"passcode": settings.STAFF_PASSCODE}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        
        # Verify JWT structure and content
        token = data["token"]
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "staff"
        assert "exp" in payload

def test_login_invalid_passcode():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/staff/login",
            json={"passcode": "wrongpasscode"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid passcode"

def test_protected_routes_without_token():
    with TestClient(app) as client:
        # Chat route
        chat_res = client.post(
            "/api/v1/chat/staff",
            json={"message": "What is the status of Gate 1?"}
        )
        assert chat_res.status_code == 401
        
        # Alerts route
        alerts_res = client.get("/api/v1/staff/alerts")
        assert alerts_res.status_code == 401

def test_protected_routes_invalid_token():
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer invalidtokenhere"}
        chat_res = client.post(
            "/api/v1/chat/staff",
            json={"message": "What is the status of Gate 1?"},
            headers=headers
        )
        assert chat_res.status_code == 401
        assert "Invalid authentication credentials" in chat_res.json()["detail"]

def test_protected_routes_expired_token():
    # Construct an expired token manually
    expired_payload = {
        "sub": "staff",
        "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=10)
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm="HS256")
    
    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {expired_token}"}
        chat_res = client.post(
            "/api/v1/chat/staff",
            json={"message": "What is the status of Gate 1?"},
            headers=headers
        )
        assert chat_res.status_code == 401
        assert "Token has expired" in chat_res.json()["detail"]

def test_protected_routes_valid_token():
    with TestClient(app) as client:
        # Get valid token
        login_res = client.post(
            "/api/v1/auth/staff/login",
            json={"passcode": settings.STAFF_PASSCODE}
        )
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Inject Mock LLM Client to prevent querying external APIs during tests
        import backend.app.routers.chat
        original_query = backend.app.routers.chat.query_stadium_assistant
        backend.app.routers.chat.query_stadium_assistant = lambda msg, is_staff, client=None, *args, **kwargs: {"reply": "Mock reply"}
        
        try:
            # Check chat route
            chat_res = client.post(
                "/api/v1/chat/staff",
                json={"message": "What is the status of Gate 1?"},
                headers=headers
            )
            assert chat_res.status_code == 200
            assert chat_res.json()["reply"] == "Mock reply"
            
            # Check alerts route
            alerts_res = client.get("/api/v1/staff/alerts", headers=headers)
            assert alerts_res.status_code == 200
        finally:
            backend.app.routers.chat.query_stadium_assistant = original_query

def test_staff_rate_limiting():
    # The staff rate limit is 30 requests per 10 seconds.
    # Let's perform 31 requests and ensure the 31st returns 429.
    test_ip = "127.0.0.1"
    
    # Mock get_staff_alerts to prevent slow LLM calls during rate limit test
    import backend.app.routers.alerts
    original_get_alerts = backend.app.routers.alerts.get_staff_alerts
    backend.app.routers.alerts.get_staff_alerts = lambda: []
    
    try:
        with TestClient(app) as client:
            # Get valid token
            login_res = client.post(
                "/api/v1/auth/staff/login",
                json={"passcode": settings.STAFF_PASSCODE}
            )
            token = login_res.json()["token"]
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Forwarded-For": test_ip
            }
            
            # Run 30 requests (which should succeed)
            for _ in range(30):
                res = client.get("/api/v1/staff/alerts", headers=headers)
                assert res.status_code == 200
                
            # The 31st request should be rate-limited
            res_limit = client.get("/api/v1/staff/alerts", headers=headers)
            assert res_limit.status_code == 429
            assert "Too many requests" in res_limit.json()["detail"]
    finally:
        backend.app.routers.alerts.get_staff_alerts = original_get_alerts
