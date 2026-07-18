"""Groq LLM client and the shared result/tool-call types.

The offline test double lives in backend.app.mock_llm; both clients expose the
same generate / generate_stream interface so the orchestrator can swap them freely.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Iterator, Optional

import httpx

from backend.app.config import settings

logger = logging.getLogger("llm_client")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 15.0
MAX_COMPLETION_TOKENS = 150   # strict cap: chat replies are meant to be short
MAX_HISTORY_MESSAGES = 4      # keep payloads light and inside token limits

# OpenAI-style schemas for the twin-query tools (single source; mirrors backend.app.tools).
OPENAI_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_route",
            "description": "Retrieves the routing path between two locations, filtering for wheelchair accessibility if required.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_location": {
                        "type": "string",
                        "description": "Start point (e.g., 'Gate 1', 'Gate 2')",
                    },
                    "to_location": {
                        "type": "string",
                        "description": "Destination point (e.g., 'Section 102', 'Section 204')",
                    },
                    "accessibility_required": {
                        "type": "boolean",
                        "description": "True if step-free accessible route is needed.",
                    },
                },
                "required": ["from_location", "to_location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crowd_density",
            "description": "Gets the current crowd density and capacity information for a specific stadium zone or concourse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {
                        "type": "string",
                        "description": "The zone ID (e.g. 'Zone-A', 'Zone-B', 'Zone-C') or zone name.",
                    },
                },
                "required": ["zone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_gate_status",
            "description": "Gets the status (open/closed) and congestion level of all stadium gates.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


@dataclass
class ToolCall:
    name: str
    args: dict

    def to_dict(self) -> dict:
        return {"name": self.name, "args": self.args}


@dataclass
class LLMResult:
    reply: str
    tool_calls: list = field(default_factory=list)


class GroqLLMClient:
    provider_name = "groq"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = settings.GROQ_MODEL
        logger.info(f"GroqLLMClient initialized using model {self.model}.")

    def _build_payload(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list],
        response_format: Optional[dict],
        history: Optional[list],
        stream: bool = False,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_message, history),
            "temperature": 0.1,
            "max_tokens": MAX_COMPLETION_TOKENS,
        }
        if stream:
            payload["stream"] = True
        if response_format:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = OPENAI_TOOL_SCHEMAS
            payload["tool_choice"] = "auto"
        return payload

    @property
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @staticmethod
    def _build_messages(system_prompt: str, user_message: str, history: Optional[list]) -> list:
        """Normalize prior turns (dicts or pydantic models) into OpenAI chat messages."""
        full_history = []
        for msg in history or []:
            if isinstance(msg, dict):
                role, content = msg.get("role"), msg.get("content")
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                role, content = msg.role, msg.content
            else:
                continue
            if role and content:
                role_norm = "assistant" if role in ("bot", "assistant") else "user"
                full_history.append({"role": role_norm, "content": content})

        full_history.append({"role": "user", "content": user_message})
        recent_history = full_history[-MAX_HISTORY_MESSAGES:]
        return [{"role": "system", "content": system_prompt}] + recent_history

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list] = None,
        response_format: Optional[dict] = None,
        mode: Optional[str] = None,
        history: Optional[list] = None,
    ) -> LLMResult:
        logger.info(f"Executing Groq API call to model {self.model}.")
        payload = self._build_payload(system_prompt, user_message, tools, response_format, history)
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.post(GROQ_CHAT_URL, headers=self._headers, json=payload)
                response.raise_for_status()
                res_data = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Groq API HTTP request failed: {e}")
            raise

        choice = res_data["choices"][0]["message"]
        reply = choice.get("content") or ""
        tool_calls = [self._parse_tool_call(tc) for tc in choice.get("tool_calls") or []]
        return LLMResult(reply=reply, tool_calls=tool_calls)

    @staticmethod
    def _parse_tool_call(raw: dict) -> ToolCall:
        func = raw.get("function", {})
        try:
            args = json.loads(func.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        # Models may return "null" or a non-object for no-arg tools; coerce to {}
        # so tool_fn(**args) never receives None.
        if not isinstance(args, dict):
            args = {}
        return ToolCall(name=func.get("name"), args=args)

    def generate_stream(
        self,
        system_prompt: str,
        user_message: str,
        tools: Optional[list] = None,
        response_format: Optional[dict] = None,
        history: Optional[list] = None,
    ) -> Iterator[dict]:
        """Yield raw OpenAI-style stream deltas ({'content': ...} / {'tool_calls': ...})."""
        logger.info(f"Executing Groq streaming API call to model {self.model}.")
        payload = self._build_payload(system_prompt, user_message, tools, response_format, history, stream=True)
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                with client.stream("POST", GROQ_CHAT_URL, headers=self._headers, json=payload) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[len("data: "):]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            yield chunk["choices"][0].get("delta", {})
                        except (json.JSONDecodeError, LookupError):
                            continue
        except httpx.HTTPError as e:
            logger.error(f"Groq stream request failed: {e}")
            raise
