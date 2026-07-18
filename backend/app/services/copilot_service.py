"""Operations Copilot — proactive, forecast-driven decision support.

Unlike the reactive chat assistant (which answers questions on demand), the Copilot
continuously reads the digital twin, projects each zone's congestion a few minutes
ahead from its recent trend, and uses GenAI to synthesize an executive situation
summary plus prioritized, specific recommended actions. Falls back to a fully
deterministic report when no LLM is available (offline / mock mode).
"""
import json
import time
import logging

from backend.app.config import settings
from backend.app.database import db_connection
from backend.app.telemetry import get_telemetry
from backend.app.services.alert_service import extract_and_parse_json

logger = logging.getLogger("services.copilot")

HORIZON_SECONDS = 300          # forecast 5 minutes ahead
CRITICAL_DENSITY = 0.85
WARNING_DENSITY = 0.70
TREND_EPS = 0.0002             # per-second slope below this is treated as "stable"


def _slope_per_second(history: list) -> float:
    """Least-squares slope of density vs. time (density units per second)."""
    if len(history) < 3:
        return 0.0
    t0 = history[0][0]
    xs = [h[0] - t0 for h in history]
    ys = [h[1] for h in history]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    num = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    return num / denom


def compute_forecast() -> dict:
    """Read the current twin state + telemetry and project each zone forward."""
    telemetry = get_telemetry()
    with db_connection() as conn:
        zones = [dict(r) for r in conn.execute(
            "SELECT id, name, type, capacity, current_crowd, density FROM zones"
        ).fetchall()]
        gates = [dict(r) for r in conn.execute(
            "SELECT id, name, status, congestion_level, zone_id FROM gates"
        ).fetchall()]

    risks = []
    for z in zones:
        history = telemetry.get(z["id"])
        slope = _slope_per_second(history)
        projected = max(0.0, min(1.0, z["density"] + slope * HORIZON_SECONDS))

        eta_seconds = None
        if slope > 1e-6 and z["density"] < CRITICAL_DENSITY:
            eta = (CRITICAL_DENSITY - z["density"]) / slope
            if 0 < eta <= HORIZON_SECONDS * 2:
                eta_seconds = int(eta)

        if slope > TREND_EPS:
            trend = "rising"
        elif slope < -TREND_EPS:
            trend = "falling"
        else:
            trend = "stable"

        feeding_gates = [g["name"] for g in gates if g["zone_id"] == z["id"]]

        risks.append({
            "zone_id": z["id"],
            "zone_name": z["name"],
            "current_density": round(z["density"], 2),
            "projected_density": round(projected, 2),
            "trend": trend,
            "slope_per_min": round(slope * 60, 4),
            "eta_minutes": round(eta_seconds / 60, 1) if eta_seconds is not None else None,
            "current_crowd": z["current_crowd"],
            "capacity": z["capacity"],
            "feeding_gates": feeding_gates,
            "risk_score": round(max(z["density"], projected), 3),
        })

    risks.sort(key=lambda r: r["risk_score"], reverse=True)
    return {"zones": zones, "gates": gates, "risks": risks}


def _notable(risks: list) -> list:
    """Zones worth surfacing: already busy, projected busy, or actively rising."""
    out = []
    for r in risks:
        if (
            r["current_density"] >= 0.60
            or r["projected_density"] >= WARNING_DENSITY
            or (r["trend"] == "rising" and r["current_density"] >= 0.50)
        ):
            out.append(r)
    return out[:3]


def _deterministic_report(top: list) -> dict:
    """Rule-based summary + recommendations used offline and as the LLM fallback."""
    if not top:
        return {
            "summary": "All zones are operating within nominal capacity. No congestion interventions are required at this time.",
            "recommendations": [],
        }

    recommendations = []
    for r in top:
        gates = ", ".join(r["feeding_gates"]) or "feeding gates"
        if r["current_density"] >= CRITICAL_DENSITY or r["projected_density"] >= CRITICAL_DENSITY:
            recommendations.append({
                "priority": "high",
                "zone": r["zone_name"],
                "action": (
                    f"Critical load at {r['zone_name']} ({int(r['current_density']*100)}%). Halt inflow at {gates}, "
                    f"open overflow routing to lower-density concourses, and deploy crowd-control stewards now."
                ),
            })
        elif r["trend"] == "rising" and r["projected_density"] >= WARNING_DENSITY:
            eta_txt = f" (~{r['eta_minutes']} min to critical)" if r["eta_minutes"] is not None else ""
            recommendations.append({
                "priority": "medium",
                "zone": r["zone_name"],
                "action": (
                    f"{r['zone_name']} is trending up toward {int(r['projected_density']*100)}%{eta_txt}. "
                    f"Pre-position stewards and begin soft redirection of arrivals away from {gates}."
                ),
            })

    lead = top[0]
    summary = (
        f"{lead['zone_name']} is the primary pressure point at {int(lead['current_density']*100)}% and {lead['trend']}, "
        f"projected to reach {int(lead['projected_density']*100)}% within {HORIZON_SECONDS // 60} minutes. "
        f"{len(recommendations)} recommended action(s) queued."
    )
    return {"summary": summary, "recommendations": recommendations}


def generate_copilot_report(use_llm: bool = True) -> dict:
    """Produce the full Operations Copilot report (forecast + summary + actions)."""
    forecast = compute_forecast()
    top = _notable(forecast["risks"])
    deterministic = _deterministic_report(top)

    provider = "mock"
    summary = deterministic["summary"]
    recommendations = deterministic["recommendations"]

    use_groq = use_llm and settings.GROQ_API_KEY and not settings.is_exhausted("groq")
    if use_groq and top:
        try:
            from backend.app.llm_client import GroqLLMClient
            system_prompt = (
                "You are EktaAI Operations Copilot, a proactive decision-support engine for FIFA World Cup 2026 "
                "stadium operations. You are given a short-horizon congestion forecast. Produce a concise executive "
                "situation summary and a prioritized list of specific, actionable recommendations for venue staff. "
                "Always return JSON with exactly these keys: 'summary' (string) and 'recommendations' (a list of "
                "objects each with 'priority' one of 'high'|'medium'|'low', 'zone' (string), and 'action' (string)). "
                "Be precise and operational; reference concrete zones and gates."
            )
            facts = [
                {
                    "zone": r["zone_name"],
                    "current_pct": int(r["current_density"] * 100),
                    "projected_5min_pct": int(r["projected_density"] * 100),
                    "trend": r["trend"],
                    "eta_minutes_to_critical": r["eta_minutes"],
                    "feeding_gates": r["feeding_gates"],
                }
                for r in top
            ]
            prompt = (
                f"Congestion forecast (5-minute horizon):\n{json.dumps(facts, indent=2)}\n\n"
                "Return the situation summary and prioritized recommendations as JSON."
            )
            llm_res = GroqLLMClient(settings.GROQ_API_KEY).generate(
                system_prompt, prompt, tools=[], response_format={"type": "json_object"}
            )
            parsed = extract_and_parse_json(llm_res.reply)
            llm_summary = parsed.get("summary")
            llm_recs = parsed.get("recommendations")
            if llm_summary and isinstance(llm_recs, list):
                summary = llm_summary
                recommendations = llm_recs
                provider = "groq"
        except Exception as e:
            logger.error(f"Copilot LLM synthesis failed: {e}. Using deterministic report.")

    return {
        "generated_at": time.time(),
        "provider": provider,
        "summary": summary,
        "recommendations": recommendations,
        "risks": top,
        "horizon_minutes": HORIZON_SECONDS // 60,
    }
