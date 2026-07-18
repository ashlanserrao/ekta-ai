import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import init_db, db_connection
from backend.app.simulator import StadiumSimulator
from backend.app.services import transit_service as ts
from backend.app.services.copilot_service import build_egress_plan, generate_copilot_report


@pytest.fixture(autouse=True)
def offline_transit():
    """Force the deterministic (offline) advisory path and a cold cache per test."""
    settings.set_exhausted("groq", True)
    ts.reset_advisory_cache()
    yield
    settings.set_exhausted("groq", False)
    ts.reset_advisory_cache()


def test_seeded_transit_lines_present():
    init_db()
    lines = ts.get_transit_lines()
    ids = {line["id"] for line in lines}
    assert {"Line-M1", "Line-M2", "Shuttle-N", "BRT-3"} <= ids
    for line in lines:
        assert 0.0 <= line["current_load"] <= 1.0
        assert 0.0 < line["minutes_to_next"] <= line["headway_minutes"]
        assert line["crowding"] in ("low", "medium", "high")
        assert line["co2_saved_kg_per_trip"] > 0


def test_crowding_labels():
    assert ts.crowding_label(0.2) == "low"
    assert ts.crowding_label(0.5) == "medium"
    assert ts.crowding_label(0.8) == "high"


def test_egress_capacity_counts_spare_seats():
    lines = [
        {"capacity_per_departure": 100, "current_load": 0.5, "headway_minutes": 5.0},
        {"capacity_per_departure": 60, "current_load": 0.0, "headway_minutes": 6.0},
    ]
    # 100*0.5/5 + 60*1.0/6 = 10 + 10 = 20 spare seats per minute
    assert ts.egress_capacity_per_minute(lines) == 20


def test_simulator_evolves_transit_load_within_bounds():
    init_db()
    sim = StadiumSimulator()
    for _ in range(5):
        sim.update_crowd_dynamics()
    for line in ts.get_transit_lines():
        assert 0.05 <= line["current_load"] <= 0.95


def test_deterministic_advisory_recommends_least_loaded_on_time_line():
    init_db()
    lines = ts.get_transit_lines()
    advisory = ts.generate_transit_advisory(lines, use_llm=False)
    assert advisory["provider"] == "mock"
    on_time = [l for l in lines if l["status"] == "on_time"]
    best = min(on_time or lines, key=lambda l: l["current_load"])
    assert best["name"] in advisory["summary"]
    # The sustainability nudge is always present
    assert any("CO2" in tip for tip in advisory["tips"])


def test_deterministic_advisory_avoids_delayed_lines():
    lines = [
        {"id": "A", "name": "Delayed Metro", "mode": "metro", "destination": "X", "status": "delayed",
         "current_load": 0.1, "minutes_to_next": 2.0, "crowding": "low",
         "capacity_per_departure": 900, "headway_minutes": 5.0, "co2_saved_kg_per_trip": 2.4},
        {"id": "B", "name": "On-Time Bus", "mode": "bus", "destination": "Y", "status": "on_time",
         "current_load": 0.6, "minutes_to_next": 3.0, "crowding": "medium",
         "capacity_per_departure": 120, "headway_minutes": 6.0, "co2_saved_kg_per_trip": 1.6},
    ]
    advisory = ts._deterministic_advisory(lines)
    assert "On-Time Bus" in advisory["summary"]
    assert any("Delayed Metro" in tip for tip in advisory["tips"])


def test_advisory_is_cached_between_calls():
    init_db()
    first = ts.generate_transit_advisory(use_llm=False)
    second = ts.generate_transit_advisory(use_llm=False)
    assert first["generated_at"] == second["generated_at"]


def test_transit_endpoint_is_public_and_complete():
    with TestClient(app) as client:
        res = client.get("/api/v1/transit")
        assert res.status_code == 200
        data = res.json()
        assert len(data["lines"]) >= 4
        assert data["egress_capacity_per_minute"] >= 0
        assert data["advisory"]["summary"]
        for line in data["lines"]:
            assert line["crowding"] in ("low", "medium", "high")


def test_egress_plan_staggers_waves_by_density():
    init_db()
    risks = [
        {"zone_name": "South Concourse C", "current_density": 0.9, "feeding_gates": ["Gate 3 (South)"]},
        {"zone_name": "East Concourse B", "current_density": 0.6, "feeding_gates": ["Gate 2 (East)"]},
    ]
    plan = build_egress_plan(risks)
    assert len(plan["waves"]) == 2
    # Densest zone releases first, with no hold; later waves are staggered
    assert plan["waves"][0]["zone"] == "South Concourse C"
    assert plan["waves"][0]["hold_minutes"] == 0
    assert plan["waves"][1]["hold_minutes"] == 5
    assert plan["transit_capacity_per_minute"] >= 0
    assert plan["sustainability_note"]
    for wave in plan["waves"]:
        assert wave["target_line"]
        assert wave["rationale"].endswith(".")


def test_copilot_report_includes_egress_plan():
    init_db()
    report = generate_copilot_report(use_llm=False)
    assert "egress_plan" in report
    assert "waves" in report["egress_plan"]
    assert "sustainability_note" in report["egress_plan"]
