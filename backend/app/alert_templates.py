"""Deterministic plain-language alert templates for twin anomalies.

Single source of truth for the rule-based alert wording used both by the alert
service (as the offline/LLM-failure fallback) and by the mock LLM client (which
simulates the GenAI translation step). Callers choose the tag style so staff-facing
alerts read "[System Alert]" while the mock GenAI path reads "[GenAI Alert]".
"""
from typing import Tuple


def deterministic_alert(
    anomaly: dict,
    alert_tag: str = "System Alert",
    action_tag: str = "Steward Action",
) -> Tuple[str, str]:
    """Translate a raw anomaly dict into a (message, recommended_action) pair."""
    if anomaly.get("type") == "zone":
        return _zone_alert(anomaly, alert_tag, action_tag)
    if anomaly.get("type") == "gate":
        return _gate_alert(anomaly, alert_tag)
    return (
        f"[{alert_tag}] General operational alert triggered.",
        f"[{action_tag}] Maintain standard stadium surveillance checks.",
    )


def _zone_alert(anomaly: dict, alert_tag: str, action_tag: str) -> Tuple[str, str]:
    name = anomaly.get("name", "Unknown Zone")
    density = anomaly.get("density", 0.0)
    current = anomaly.get("current_crowd", 0)
    if anomaly.get("severity", "info") == "critical":
        msg = (
            f"[{alert_tag}] Critical crowd surge detected at {name}. "
            f"Occupancy has reached {int(density * 100)}% capacity ({current} fans)."
        )
        act = (
            f"[{action_tag}] Immediately halt incoming ticket validation at adjacent turnstiles. "
            "Re-route arrival streams toward alternative entrances and deploy crowd control officers."
        )
    else:
        msg = f"[{alert_tag}] Crowd density is climbing at {name}, now at {int(density * 100)}%."
        act = (
            f"[{action_tag}] Activate secondary warning signage and instruct stewards "
            "to monitor local walkways for bottlenecks."
        )
    return msg, act


def _gate_alert(anomaly: dict, alert_tag: str) -> Tuple[str, str]:
    name = anomaly.get("name", "Unknown Gate")
    if anomaly.get("status", "open") == "closed":
        msg = f"[{alert_tag}] Checkpoint status change: {name} is CLOSED."
        act = "Activate digital detour guidance screens. Direct arriving spectators to nearest open gate immediately."
    else:
        msg = f"[{alert_tag}] Access restriction: {name} has transitioned to EMERGENCY EXIT ONLY."
        act = "Coordinate with emergency response units and notify nearby shuttle loops to suspend drops at this gate."
    return msg, act
