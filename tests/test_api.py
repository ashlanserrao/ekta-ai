import pytest
import time
from fastapi.testclient import TestClient
from backend.app.main import app, chat_limiter
from backend.app.database import init_db, get_db_connection
from backend.app.config import Config
from backend.app.llm_client import MockLLMClient

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Force initialize the SQLite database
    init_db()
    yield

@pytest.fixture(autouse=True)
def inject_mock_client():
    import backend.app.main
    original_query = backend.app.main.query_stadium_assistant
    
    def mock_query(user_message, is_staff=False, client=None):
        print(f"\n[TESTING - API] Injecting MockLLMClient for user_message='{user_message}' (is_staff={is_staff})")
        return original_query(user_message, is_staff=is_staff, client=MockLLMClient())
        
    backend.app.main.query_stadium_assistant = mock_query
    yield
    backend.app.main.query_stadium_assistant = original_query

def test_root_endpoint():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["app"] == "EktaAI API"

def test_stadium_status():
    with TestClient(app) as client:
        response = client.get("/api/v1/stadium/status")
        assert response.status_code == 200
        data = response.json()
        assert "gates" in data
        assert "zones" in data
        assert len(data["gates"]) == 4
        assert len(data["zones"]) == 5

def test_gates_and_zones_endpoints():
    with TestClient(app) as client:
        # Gates endpoint
        gates_res = client.get("/api/v1/stadium/gates")
        assert gates_res.status_code == 200
        assert len(gates_res.json()) == 4
        
        # Zones endpoint
        zones_res = client.get("/api/v1/stadium/zones")
        assert zones_res.status_code == 200
        assert len(zones_res.json()) == 5

def test_staff_alerts():
    with TestClient(app) as client:
        response = client.get("/api/v1/staff/alerts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "message" in data[0]
        assert "severity" in data[0]

def test_chat_endpoints():
    with TestClient(app) as client:
        # Test Fan Chat
        fan_res = client.post(
            "/api/v1/chat/fan",
            json={"message": "Where is the main medical center?", "language": "en"}
        )
        assert fan_res.status_code == 200
        fan_data = fan_res.json()
        assert "reply" in fan_data
        assert fan_data["rag_used"] is True
        assert "medical" in fan_data["reply"].lower() or "first aid" in fan_data["reply"].lower() or "guidelines" in fan_data["reply"].lower()
        
        # Test Staff Chat - Crowd Density Query
        staff_res = client.post(
            "/api/v1/chat/staff",
            json={"message": "What is the crowd density at Zone-C?"}
        )
        assert staff_res.status_code == 200
        staff_data = staff_res.json()
        assert "reply" in staff_data
        assert "[STAFF OPERATIONAL BRIEF]" in staff_data["reply"]
        assert "Zone-C" in staff_data["reply"]
        assert "90%" in staff_data["reply"]
        assert "{" not in staff_data["reply"]
        
        # Test Staff Chat - Gate Status Query
        gate_res = client.post(
            "/api/v1/chat/staff",
            json={"message": "Is Gate 2 open or closed right now?"}
        )
        assert gate_res.status_code == 200
        gate_data = gate_res.json()
        assert "reply" in gate_data
        assert "Gate 2" in gate_data["reply"]
        assert "open" in gate_data["reply"].lower()
        assert "{" not in gate_data["reply"]

def test_rate_limiting():
    # Set limit low to quickly trigger limit or just hit it repeatedly
    # Config is 5 requests per 10 seconds. Let's make 6 requests.
    # Reset limiter for the testing IP
    test_ip = "127.0.0.1"
    chat_limiter.request_timestamps[test_ip] = []
    
    with TestClient(app) as client:
        success_count = 0
        limited_triggered = False
        
        for _ in range(7):
            res = client.post(
                "/api/v1/chat/fan",
                json={"message": "ping", "language": "en"},
                headers={"X-Forwarded-For": test_ip} # Set headers if using middleware, else testclient default works
            )
            if res.status_code == 200:
                success_count += 1
            elif res.status_code == 429:
                limited_triggered = True
                
        assert limited_triggered is True
