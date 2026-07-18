import time
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.telemetry import get_telemetry
from backend.app.middleware.rate_limit import staff_limiter
from backend.app.services import copilot_service as cs


@pytest.fixture(autouse=True)
def offline_copilot():
    """Force the deterministic (offline) copilot path so tests never hit the network."""
    settings.set_exhausted("groq", True)
    yield
    settings.set_exhausted("groq", False)


def test_telemetry_record_and_get():
    tele = get_telemetry()
    tele.clear()
    tele.record("Zone-X", 0.5, 500, ts=1000.0)
    tele.record("Zone-X", 0.6, 600, ts=1003.0)
    history = tele.get("Zone-X")
    assert len(history) == 2
    assert history[0] == (1000.0, 0.5, 500)
    assert history[1] == (1003.0, 0.6, 600)


def test_slope_computation():
    # Perfectly linear rising series -> positive slope
    now = 1000.0
    hist = [(now + i * 3, 0.5 + i * 0.03, 0) for i in range(6)]
    slope = cs._slope_per_second(hist)
    assert slope > 0
    # Too few samples -> zero slope (no spurious trends)
    assert cs._slope_per_second([(1.0, 0.5, 0)]) == 0.0


def test_forecast_detects_rising_trend():
    init_db()
    tele = get_telemetry()
    tele.clear()
    now = time.time()
    for i in range(10):
        tele.record("Zone-C", 0.70 + i * 0.01, 7000 + i * 80, ts=now - (10 - i) * 3)

    forecast = cs.compute_forecast()
    zone_c = next(r for r in forecast["risks"] if r["zone_id"] == "Zone-C")
    assert zone_c["trend"] == "rising"
    assert zone_c["slope_per_min"] > 0
    assert zone_c["projected_density"] >= zone_c["current_density"]
    # Gate 3 feeds Zone-C in the seeded twin
    assert "Gate 3 (South)" in zone_c["feeding_gates"]
    # Risks are ranked by descending risk score
    scores = [r["risk_score"] for r in forecast["risks"]]
    assert scores == sorted(scores, reverse=True)


def test_report_structure_deterministic():
    init_db()
    report = cs.generate_copilot_report(use_llm=False)
    assert report["provider"] == "mock"
    assert isinstance(report["summary"], str) and report["summary"]
    assert isinstance(report["recommendations"], list)
    assert isinstance(report["risks"], list)
    assert report["horizon_minutes"] == 5
    for rec in report["recommendations"]:
        assert rec["priority"] in ("high", "medium", "low")
        assert "zone" in rec and "action" in rec


def test_copilot_endpoint_requires_auth_and_returns_report():
    staff_limiter.request_timestamps.clear()
    with TestClient(app) as client:
        # No token -> 401
        assert client.get("/api/v1/staff/copilot").status_code == 401

        # Authenticate
        login = client.post("/api/v1/auth/staff/login", json={"passcode": settings.STAFF_PASSCODE})
        assert login.status_code == 200
        token = login.json()["token"]

        res = client.get("/api/v1/staff/copilot", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "recommendations" in data
        assert "risks" in data
        assert data["provider"] in ("mock", "groq")
