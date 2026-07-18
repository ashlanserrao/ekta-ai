"""Deterministic, offline stand-in for the live LLM.

MockLLMClient mirrors the GroqLLMClient interface (generate / generate_stream) but
answers from keyword heuristics and the local RAG store, so the whole app keeps
working with no API key and no network. Each supported intent (routing, gate
status, crowd density, alert translation) lives in its own small handler.
"""
import json
import logging
import re
from typing import Iterator, Optional

from backend.app.alert_templates import deterministic_alert
from backend.app.llm_client import LLMResult, ToolCall

logger = logging.getLogger("mock_llm")

# Keyword heuristics for offline language detection. The live LLM matches the
# user's language natively; the mock only needs to pick the right canned reply.
SPANISH_HINTS = (
    "baños", "comida", "como", "llego", "en silla", "dónde", "donde",
    "restaurante", "ruta", "puerta",
)
FRENCH_HINTS = (
    "toilettes", "où", "où est", "j'arrive", "fauteuil roulant", "fauteuil",
    "nourriture", "itinéraire", "puis-je", "bonjour", "s'il vous", "aller",
    "comment aller",
)

ROUTE_HINTS = (
    "route", "get to", "go from", "directions", "how to", "how do i", "map",
    "llego", "ruta", "ir de", "ir a", "cómo", "aller", "itinéraire", "vers",
    "comment aller",
)
ACCESSIBILITY_HINTS = (
    "wheelchair", "accessible", "disabled", "ramp", "elevator", "stroller",
    "silla de ruedas", "acceso", "rampa", "ascensor", "fauteuil",
    "fauteuil roulant", "rampe", "ascenseur",
)
DENSITY_HINTS = ("density", "crowd", "capacity", "congest", "gente", "personas", "tráfico", "trafico")

# Free-text location aliases -> routing-graph node names (incl. Porte/Puerta gates).
LOCATION_ALIASES = {
    **{f"gate {n}": f"Gate {n}" for n in range(1, 5)},
    **{f"porte {n}": f"Gate {n}" for n in range(1, 5)},
    **{f"puerta {n}": f"Gate {n}" for n in range(1, 5)},
    "section 102": "Section 102 Entry",
    "section 105": "Section 105 Entry",
    "section 204": "Section 204 Entry",
    "section 305": "Section 305 Entry",
}

ZONE_IDS = ("Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-VIP")

WELCOME_REPLY = (
    "Welcome to EktaAI, your stadium assistant. "
    "How can I help you navigate the stadium or find facilities today?"
)
ALL_NORMAL_ALERT = {
    "message": "[GenAI Alert] All stadium zones and gates are operating within normal parameters.",
    "recommended_action": "[GenAI Action] Maintain standard entry checkpoints monitoring.",
}


def detect_language(normalized_msg: str) -> str:
    """Best-effort 'en'/'es'/'fr' guess from keyword hints (offline heuristic)."""
    if any(w in normalized_msg for w in FRENCH_HINTS):
        return "fr"
    if any(w in normalized_msg for w in SPANISH_HINTS):
        return "es"
    return "en"


def _strip_non_alnum(s: str) -> str:
    return "".join(c for c in s if c.isalnum())


def _parse_anomalies(user_message: str) -> tuple:
    """Pull the anomaly payload (list or single dict) out of an alert-translation prompt."""
    list_match = re.search(r"\[\s*\{.*\}\s*\]", user_message, re.DOTALL)
    if list_match:
        try:
            return json.loads(list_match.group(0)), True
        except json.JSONDecodeError:
            pass

    dict_match = re.search(r"\{.*\}", user_message, re.DOTALL)
    if dict_match:
        try:
            return [json.loads(dict_match.group(0))], False
        except json.JSONDecodeError:
            pass

    try:
        parsed = json.loads(user_message)
    except json.JSONDecodeError:
        return [], False
    if isinstance(parsed, list):
        return parsed, True
    return [parsed], False


class MockLLMClient:
    provider_name = "mock"

    def __init__(self):
        logger.info("MockLLMClient initialized.")

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list] = None,
        response_format: Optional[dict] = None,
        mode: Optional[str] = None,
        history: Optional[list] = None,
    ) -> LLMResult:
        logger.info("Executing MockLLMClient generate.")
        if mode == "alert_translation":
            return self._translate_alerts(user_message)

        msg = user_message.lower().strip()
        lang = detect_language(msg)

        result = (
            self._route_reply(msg, lang)
            or self._gate_status_reply(msg)
            or self._crowd_density_reply(msg, lang, system_prompt)
        )
        if result is not None:
            return result
        if "ping" in msg:
            return LLMResult(reply="pong")
        return self._rag_fallback_reply(user_message, msg, lang)

    def generate_stream(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list] = None,
        response_format: Optional[dict] = None,
        mode: Optional[str] = None,
        history: Optional[list] = None,
    ) -> Iterator[dict]:
        """Yield OpenAI-style stream deltas built from the non-streaming result."""
        logger.info("Executing MockLLMClient generate_stream.")
        res = self.generate(system_prompt, user_message, tools, response_format, mode, history=history)

        if res.tool_calls:
            yield {
                "tool_calls": [
                    {"index": idx, "function": {"name": tc.name, "arguments": json.dumps(tc.args)}}
                    for idx, tc in enumerate(res.tool_calls)
                ]
            }
            return

        for idx, word in enumerate(res.reply.split(" ")):
            yield {"content": (" " if idx > 0 else "") + word}

    # --- Intent handlers -------------------------------------------------

    def _translate_alerts(self, user_message: str) -> LLMResult:
        """Simulate the GenAI 'anomaly -> plain-language alert' translation step."""
        anomalies, is_batch = _parse_anomalies(user_message)

        alerts = []
        for anomaly in anomalies:
            if anomaly.get("type") in ("zone", "gate"):
                msg, act = deterministic_alert(anomaly, alert_tag="GenAI Alert", action_tag="GenAI Action")
                alerts.append({"message": msg, "recommended_action": act})
            else:
                alerts.append(dict(ALL_NORMAL_ALERT))

        if is_batch:
            return LLMResult(reply=json.dumps({"alerts": alerts}))
        return LLMResult(reply=json.dumps(alerts[0] if alerts else ALL_NORMAL_ALERT))

    def _route_reply(self, msg: str, lang: str) -> Optional[LLMResult]:
        """Detect a routing request, emit a get_route tool call plus a canned confirmation."""
        if not any(w in msg for w in ROUTE_HINTS):
            return None

        msg_norm = _strip_non_alnum(msg)
        found = [key for key in LOCATION_ALIASES if _strip_non_alnum(key) in msg_norm]
        if not found:
            return None

        accessible = any(w in msg for w in ACCESSIBILITY_HINTS)

        if len(found) >= 2:
            # Order the two mentioned locations by their position in the message.
            first, second = sorted(found[:2], key=msg.find)
            from_location, to_location = LOCATION_ALIASES[first], LOCATION_ALIASES[second]
        else:
            # Single location mentioned: treat it as the destination from a default gate.
            to_location = LOCATION_ALIASES[found[0]]
            from_location = "Gate 2" if to_location == "Gate 1" else "Gate 1"

        tool_call = ToolCall("get_route", {
            "from_location": from_location,
            "to_location": to_location,
            "accessibility_required": accessible,
        })

        if lang == "fr":
            reply = (
                f"J'ai tracé un itinéraire {'accessible ' if accessible else ''}de {from_location} "
                f"à {to_location}. Je l'ai chargé sur la carte interactive."
            )
        elif lang == "es":
            reply = (
                f"He trazado una ruta accesible de {from_location} a {to_location}. "
                "He cargado la ruta accesible en el mapa interactivo."
            )
        else:
            reply = (
                f"Sure! I have generated a {'step-free accessible ' if accessible else 'standard '}route "
                f"from {from_location} to {to_location}. I've highlighted the path on your map."
            )
        return LLMResult(reply=reply, tool_calls=[tool_call])

    def _gate_status_reply(self, msg: str) -> Optional[LLMResult]:
        is_status_query = (
            "gate" in msg
            and any(w in msg for w in ("status", "open", "closed", "state"))
            and not any(w in msg for w in ("hour", "time", "when", "restriction", "policy"))
        )
        if not is_status_query:
            return None
        reply = "Here is the status of the gates."
        if "gate 2" in msg:
            reply = "Here is the status of the gates: Gate 2 (East) is open."
        return LLMResult(reply=reply, tool_calls=[ToolCall("get_gate_status", {})])

    def _crowd_density_reply(self, msg: str, lang: str, system_prompt: str) -> Optional[LLMResult]:
        if not any(w in msg for w in DENSITY_HINTS):
            return None

        target_zone = next((z for z in ZONE_IDS if z.lower() in msg), "Zone-C")
        tool_call = ToolCall("get_crowd_density", {"zone": target_zone})

        if "staff" in system_prompt.lower() or "operational" in system_prompt.lower():
            reply = (
                f"[STAFF OPERATIONAL BRIEF] Zone {target_zone} (South Concourse C) is at 90% capacity. "
                "Congestion status is active."
            )
        elif lang == "fr":
            reply = "Le niveau d'affluence dans le Concourse C Sud est actuellement à 90% de sa capacité."
        elif lang == "es":
            reply = "El nivel de afluencia en South Concourse C está actualmente al 90% de su capacidad."
        else:
            reply = "The crowd level in South Concourse C is currently at 90% capacity."
        return LLMResult(reply=reply, tool_calls=[tool_call])

    def _rag_fallback_reply(self, user_message: str, msg: str, lang: str) -> LLMResult:
        """Answer general questions from the local RAG store, with language-aware phrasing."""
        try:
            from backend.app.rag import get_rag  # deferred: avoids embedding-lib import at module load

            rag_results = get_rag().retrieve(user_message, top_k=1)
        except Exception as e:
            logger.error(f"Dynamic RAG search failed: {e}")
            return LLMResult(reply=WELCOME_REPLY)

        if not rag_results or rag_results[0]["similarity"] <= 0:
            return LLMResult(reply=WELCOME_REPLY)

        content = rag_results[0]["content"]
        if lang == "fr":
            if "toilettes" in msg:
                return LLMResult(reply=(
                    "Les toilettes accessibles se trouvent à tous les niveaux, "
                    "près des sections 104, 112, 205, 220, 304 et 318."
                ))
            return LLMResult(reply=f"D'après les informations du stade : {content}")
        if lang == "es":
            if "baños" in msg or "banos" in msg:
                return LLMResult(reply=(
                    "Los baños accesibles están en todos los niveles "
                    "cerca de las secciones 104, 112, 205, 220, 304 y 318."
                ))
            if "halal" in msg or "vegetariana" in msg:
                return LLMResult(reply=(
                    "De acuerdo a la información del estadio: "
                    "Concourse A features certified Halal food stalls at Section 105."
                ))
            return LLMResult(reply=f"De acuerdo a la información del estadio: {content}")
        return LLMResult(reply=f"According to stadium guidelines: {content}")
