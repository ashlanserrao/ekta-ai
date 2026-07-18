"""GenAI-translated staff alerts from digital-twin anomalies.

Scans the twin for anomalies (closed gates, high-density zones), then asks the
LLM to translate the whole batch into plain-language alerts + steward actions in
a single request. Every step has a deterministic fallback (shared templates in
backend.app.alert_templates), so alerts keep flowing with no LLM available.
"""
import json
import logging
import re
from collections import OrderedDict
from typing import List, Optional, Tuple

from backend.app.alert_templates import deterministic_alert
from backend.app.config import settings
from backend.app.database import db_connection
from backend.app.llm_client import GroqLLMClient
from backend.app.mock_llm import MockLLMClient
from backend.app.models import PlainLanguageAlert
from backend.app.services.orchestrator import execute_with_retry_and_circuit_breaker

logger = logging.getLogger("services.alert")

ZONE_WARNING_DENSITY = 0.70
ZONE_CRITICAL_DENSITY = 0.85

# Bounded LRU of translated alert batches, keyed by the anomalies' identity/state.
# Avoids re-asking the LLM while the twin state is unchanged between polls.
ALERT_CACHE_MAX_ENTRIES = 128
_alert_cache: "OrderedDict[tuple, list]" = OrderedDict()

BATCH_SYSTEM_PROMPT = (
    "You are EktaAI, an operational intelligence engine for FIFA World Cup 2026. "
    "You translate a list of raw stadium sensor anomalies into professional plain-language alerts "
    "and action items. Always return response in JSON format. The response must be a JSON object "
    "containing an 'alerts' key, which maps to a list of alert objects. Each alert object "
    "must have exactly two keys: 'message' and 'recommended_action', corresponding order-by-order "
    "to the list of anomalies in the prompt."
)


def extract_and_parse_json(text: str) -> dict:
    """Cleanly parse a JSON dictionary block out of a raw LLM response."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed parsing JSON from text: {e}")


def _batch_cache_key(anomalies_list: list) -> tuple:
    return tuple(
        (a.get("id"), a.get("status", ""), a.get("density", 0.0)) for a in anomalies_list
    )


def _cache_get(key: tuple) -> Optional[list]:
    if key in _alert_cache:
        _alert_cache.move_to_end(key)
        return list(_alert_cache[key])
    return None


def _cache_put(key: tuple, value: list) -> None:
    _alert_cache[key] = list(value)
    _alert_cache.move_to_end(key)
    while len(_alert_cache) > ALERT_CACHE_MAX_ENTRIES:
        _alert_cache.popitem(last=False)


def _llm_translate_batch(anomalies_list: list) -> Optional[list]:
    """Ask the LLM (Groq, then mock) to translate anomalies; None if parsing fails."""
    prompt = (
        f"List of raw anomalies to translate:\n"
        f"{json.dumps(anomalies_list)}\n\n"
        f"Translate each anomaly in order. Return a JSON object with keys: "
        f"alerts (list of objects with message and recommended_action)."
    )

    llm_res = None
    if settings.GROQ_API_KEY:
        logger.info("Batch Alerts: Attempting with Groq provider.")
        llm_res, _ = execute_with_retry_and_circuit_breaker(
            "groq",
            lambda: GroqLLMClient(settings.GROQ_API_KEY),
            BATCH_SYSTEM_PROMPT,
            prompt,
            tools=[],
            response_format={"type": "json_object"},
            mode="alert_translation",
        )
    if llm_res is None:
        logger.info("Batch Alerts: Selecting Mock client (Fallback)")
        llm_res = MockLLMClient().generate(BATCH_SYSTEM_PROMPT, prompt, tools=[], mode="alert_translation")

    try:
        parsed = extract_and_parse_json(llm_res.reply)
    except ValueError as e:
        logger.error(f"Batch alerts parsing failed: {e}. Raw response: {llm_res.reply!r}")
        return None

    alerts = parsed.get("alerts")
    return alerts if isinstance(alerts, list) else None


def generate_alerts_batch_with_llm(anomalies_list: list) -> list:
    """Translate anomalies into plain-language alerts in one LLM request.

    Any anomaly the LLM output misses (or a wholesale parse failure) falls back to
    the deterministic template, so the result always covers every anomaly in order.
    """
    cache_key = _batch_cache_key(anomalies_list)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    fallbacks = [deterministic_alert(a) for a in anomalies_list]
    translated = _llm_translate_batch(anomalies_list) or []

    result = []
    for idx, anomaly in enumerate(anomalies_list):
        fallback_msg, fallback_act = fallbacks[idx]
        llm_alert = translated[idx] if idx < len(translated) else {}
        result.append({
            "id": anomaly["id"],
            "message": llm_alert.get("message", fallback_msg),
            "recommended_action": llm_alert.get("recommended_action", fallback_act),
            "severity": anomaly["severity"],
        })

    _cache_put(cache_key, result)
    return result


def _scan_twin_for_anomalies() -> list:
    """Read the twin and collect gate/zone states that warrant a staff alert."""
    anomalies = []
    with db_connection() as conn:
        for row in conn.execute(
            "SELECT id, name, status, congestion_level FROM gates WHERE status = 'closed'"
        ).fetchall():
            anomalies.append({
                "type": "gate",
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
                "congestion": row["congestion_level"],
                "severity": "warning",
            })

        for row in conn.execute(
            "SELECT id, name, type, capacity, current_crowd, density FROM zones WHERE density >= ?",
            (ZONE_WARNING_DENSITY,),
        ).fetchall():
            anomalies.append({
                "type": "zone",
                "id": row["id"],
                "name": row["name"],
                "capacity": row["capacity"],
                "current_crowd": row["current_crowd"],
                "density": row["density"],
                "severity": "critical" if row["density"] >= ZONE_CRITICAL_DENSITY else "warning",
            })
    return anomalies


def get_staff_alerts() -> List[PlainLanguageAlert]:
    """Scan the digital twin and return plain-language alerts for current anomalies."""
    anomalies = _scan_twin_for_anomalies()
    if not anomalies:
        return []

    try:
        return generate_alerts_batch_with_llm(anomalies)
    except Exception as e:
        logger.error(f"GenAI batch alerts translation failed: {e}. Using local fallback translations.")
        results = []
        for anomaly in anomalies:
            msg, act = deterministic_alert(anomaly)
            results.append({
                "id": anomaly["id"],
                "message": msg,
                "recommended_action": act,
                "severity": anomaly["severity"],
            })
        return results
