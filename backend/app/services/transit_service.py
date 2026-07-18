"""Transportation & sustainable-travel intelligence from the digital twin.

Reads the live transit_lines state (loads evolved by the simulator), computes
next departures and crowding, and produces a GenAI departure advisory nudging
fans toward the greenest, least-crowded way home. Follows the platform pattern:
the LLM synthesizes, the twin is the source of truth, and a deterministic
fallback keeps the feature fully functional offline.
"""
import json
import logging
import threading
import time
from typing import List, Optional

from backend.app.config import settings
from backend.app.database import db_connection
from backend.app.llm_client import GroqLLMClient
from backend.app.services.alert_service import extract_and_parse_json

logger = logging.getLogger("services.transit")

HIGH_LOAD = 0.75
MEDIUM_LOAD = 0.40

# Advisory cache: transit guidance changes slowly, so avoid an LLM call per poll.
ADVISORY_TTL_SECONDS = 60.0

# Approximate CO2 saved per fan choosing this mode over a solo car trip
# (10 km average trip; indicative figures for the sustainability nudge).
CO2_SAVED_PER_TRIP_KG = {"metro": 2.4, "rail": 2.4, "shuttle": 1.8, "bus": 1.6}

# Fixed schedule epoch so departure countdowns are deterministic and stable
# across requests (midnight UTC of the current day would drift; a constant won't).
_SCHEDULE_EPOCH = 0.0

_advisory_lock = threading.Lock()
_advisory_cache: Optional[dict] = None
_advisory_cached_at = 0.0


def crowding_label(load: float) -> str:
    if load > HIGH_LOAD:
        return "high"
    if load >= MEDIUM_LOAD:
        return "medium"
    return "low"


def _minutes_to_next_departure(headway_minutes: float, now: Optional[float] = None) -> float:
    """Countdown to the next scheduled departure on a fixed-headway timetable."""
    now = now if now is not None else time.time()
    elapsed_minutes = (now - _SCHEDULE_EPOCH) / 60.0
    remainder = elapsed_minutes % headway_minutes
    return round(headway_minutes - remainder, 1)


def get_transit_lines() -> List[dict]:
    """Live transit lines with next-departure countdowns and crowding labels."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, mode, destination, headway_minutes, capacity_per_departure, "
            "current_load, status FROM transit_lines"
        ).fetchall()

    lines = []
    for row in rows:
        line = dict(row)
        line["minutes_to_next"] = _minutes_to_next_departure(line["headway_minutes"])
        line["crowding"] = crowding_label(line["current_load"])
        line["co2_saved_kg_per_trip"] = CO2_SAVED_PER_TRIP_KG.get(line["mode"], 1.5)
        lines.append(line)
    return lines


def egress_capacity_per_minute(lines: List[dict]) -> int:
    """Total spare outbound seats per minute across all running lines."""
    total = 0.0
    for line in lines:
        spare_per_departure = line["capacity_per_departure"] * (1.0 - line["current_load"])
        total += spare_per_departure / line["headway_minutes"]
    return int(total)


def _deterministic_advisory(lines: List[dict]) -> dict:
    """Rule-based departure guidance used offline and as the LLM fallback."""
    if not lines:
        return {"summary": "No transit lines are currently reporting. Please check signage on site.", "tips": []}

    # Recommend the emptiest on-time line; fall back to any line if all are delayed.
    on_time = [l for l in lines if l["status"] == "on_time"]
    best = min(on_time or lines, key=lambda l: l["current_load"])
    delayed = [l for l in lines if l["status"] == "delayed"]
    crowded = [l for l in lines if l["crowding"] == "high"]

    summary = (
        f"{best['name']} toward {best['destination']} is your best way home right now "
        f"({int(best['current_load'] * 100)}% full, next departure in ~{int(best['minutes_to_next'])} min)."
    )

    tips = []
    if crowded:
        names = ", ".join(l["name"] for l in crowded)
        tips.append(f"Expect queues on {names} — consider waiting out the first post-match rush at a concourse concession.")
    for line in delayed:
        tips.append(f"{line['name']} is running delayed; allow extra time or use an alternative line.")
    tips.append(
        f"Taking the {best['mode']} instead of a car saves about {best['co2_saved_kg_per_trip']} kg of CO2 per person on this trip."
    )
    return {"summary": summary, "tips": tips}


def generate_transit_advisory(lines: Optional[List[dict]] = None, use_llm: bool = True) -> dict:
    """Produce the (cached) departure advisory: LLM-composed when available."""
    global _advisory_cache, _advisory_cached_at

    with _advisory_lock:
        if _advisory_cache is not None and time.time() - _advisory_cached_at < ADVISORY_TTL_SECONDS:
            return _advisory_cache

    if lines is None:
        lines = get_transit_lines()

    provider = "mock"
    advisory = _deterministic_advisory(lines)

    use_groq = use_llm and settings.GROQ_API_KEY and not settings.is_exhausted("groq")
    if use_groq and lines:
        try:
            system_prompt = (
                "You are EktaAI Transit Advisor for FIFA World Cup 2026 stadium operations. Given live "
                "transit-line telemetry, write a short, friendly departure advisory for fans. Encourage "
                "public transit and mention the least-crowded option and any delays. Always return JSON "
                "with exactly these keys: 'summary' (string, max 2 sentences) and 'tips' (list of at most "
                "3 short strings, including one sustainability nudge)."
            )
            facts = [
                {
                    "line": l["name"],
                    "mode": l["mode"],
                    "destination": l["destination"],
                    "load_pct": int(l["current_load"] * 100),
                    "next_departure_min": int(l["minutes_to_next"]),
                    "status": l["status"],
                    "co2_saved_kg_vs_car": l["co2_saved_kg_per_trip"],
                }
                for l in lines
            ]
            prompt = (
                f"Live transit telemetry:\n{json.dumps(facts, indent=2)}\n\n"
                "Return the departure advisory as JSON."
            )
            llm_res = GroqLLMClient(settings.GROQ_API_KEY).generate(
                system_prompt, prompt, tools=[], response_format={"type": "json_object"}
            )
            parsed = extract_and_parse_json(llm_res.reply)
            if parsed.get("summary") and isinstance(parsed.get("tips"), list):
                advisory = {"summary": parsed["summary"], "tips": parsed["tips"]}
                provider = "groq"
        except Exception as e:
            logger.error(f"Transit advisory LLM synthesis failed: {e}. Using deterministic advisory.")

    result = {
        "generated_at": time.time(),
        "provider": provider,
        "summary": advisory["summary"],
        "tips": advisory["tips"],
    }
    with _advisory_lock:
        _advisory_cache = result
        _advisory_cached_at = time.time()
    return result


def reset_advisory_cache() -> None:
    """Test hook: clear the cached advisory."""
    global _advisory_cache, _advisory_cached_at
    with _advisory_lock:
        _advisory_cache = None
        _advisory_cached_at = 0.0
