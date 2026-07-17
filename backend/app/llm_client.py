import os
import re
import json
import logging

logger = logging.getLogger("llm_client")

class ToolCall:
    def __init__(self, name: str, args: dict):
        self.name = name
        self.args = args

    def to_dict(self):
        return {"name": self.name, "args": self.args}

    def __repr__(self):
        return f"ToolCall(name={self.name}, args={self.args})"

class LLMResult:
    def __init__(self, reply: str, tool_calls: list = None):
        self.reply = reply
        self.tool_calls = tool_calls or []

    def __repr__(self):
        return f"LLMResult(reply={self.reply[:50]}..., tool_calls={self.tool_calls})"

class MockLLMClient:
    provider_name = "mock"
    def __init__(self):
        logger.info("MockLLMClient initialized.")

    def generate(self, system_prompt: str, user_message: str, tools: list = None, response_format: dict = None, mode: str = None, history: list = None) -> LLMResult:
        logger.info("Executing MockLLMClient generate.")
        
        # 0. Check if this is an operational alert translation request
        if mode == "alert_translation":
            import re
            list_match = re.search(r"\[\s*\{.*\}\s*\]", user_message, re.DOTALL)
            anomalies = []
            is_batch = False
            if list_match:
                try:
                    anomalies = json.loads(list_match.group(0))
                    is_batch = True
                except Exception:
                    pass
            
            if not anomalies:
                dict_match = re.search(r"\{.*\}", user_message, re.DOTALL)
                if dict_match:
                    try:
                        anomalies = [json.loads(dict_match.group(0))]
                    except Exception:
                        pass
            
            if not anomalies:
                try:
                    anomalies = json.loads(user_message)
                    if not isinstance(anomalies, list):
                        anomalies = [anomalies]
                    else:
                        is_batch = True
                except Exception:
                    anomalies = []
                
            mock_alerts = []
            for anomaly in anomalies:
                if anomaly.get("type") == "zone":
                    name = anomaly.get("name", "Unknown Zone")
                    density = anomaly.get("density", 0.0)
                    current = anomaly.get("current_crowd", 0)
                    severity = anomaly.get("severity", "info")
                    if severity == "critical":
                        msg = f"[GenAI Alert] Critical crowd surge detected at {name}. Occupancy has reached {int(density*100)}% capacity ({current} fans)."
                        act = "[GenAI Action] Immediately halt incoming ticket validation at adjacent turnstiles. Re-route arrival streams toward alternative entrances and deploy crowd control officers."
                    else:
                        msg = f"[GenAI Alert] Crowd density is climbing at {name}, now at {int(density*100)}%."
                        act = "[GenAI Action] Activate secondary warning signage and instruct stewards to monitor local walkways for bottlenecks."
                elif anomaly.get("type") == "gate":
                    name = anomaly.get("name", "Unknown Gate")
                    status = anomaly.get("status", "open")
                    if status == "closed":
                        msg = f"[GenAI Alert] Checkpoint status change: {name} is CLOSED."
                        act = "Activate digital detour guidance screens. Direct arriving spectators to nearest open gate immediately."
                    else:
                        msg = f"[GenAI Alert] Access restriction: {name} has transitioned to EMERGENCY EXIT ONLY."
                        act = "Coordinate with emergency response units and notify nearby shuttle loops to suspend drops at this gate."
                else:
                    msg = "[GenAI Alert] All stadium zones and gates are operating within normal parameters."
                    act = "[GenAI Action] Maintain standard entry checkpoints monitoring."
                
                mock_alerts.append({
                    "message": msg,
                    "recommended_action": act
                })
            
            if is_batch:
                return LLMResult(reply=json.dumps({"alerts": mock_alerts}), tool_calls=[])
            else:
                if mock_alerts:
                    return LLMResult(reply=json.dumps(mock_alerts[0]), tool_calls=[])
                else:
                    return LLMResult(reply=json.dumps({
                        "message": "[GenAI Alert] All stadium zones and gates are operating within normal parameters.",
                        "recommended_action": "[GenAI Action] Maintain standard entry checkpoints monitoring."
                    }), tool_calls=[])

        normalized_msg = user_message.lower().strip()
        tool_calls = []
        reply = ""

        # Determine language (Spanish if query contains key Spanish words)
        is_spanish = any(w in normalized_msg for w in ["baños", "comida", "como", "llego", "en silla", "dónde", "donde", "restaurante", "ruta", "puerta"])

        # 1. Check for Route Planning Queries
        locations = {
            "gate 1": "Gate 1",
            "gate 2": "Gate 2",
            "gate 3": "Gate 3",
            "gate 4": "Gate 4",
            "section 102": "Section 102 Entry",
            "section 105": "Section 105 Entry",
            "section 204": "Section 204 Entry",
            "section 305": "Section 305 Entry"
        }
        
        # Normalize message to alphanumeric only for robust location matching in Mock client
        msg_norm = "".join(c for c in normalized_msg if c.isalnum())
        
        found_keys = []
        for key in locations.keys():
            key_norm = "".join(c for c in key if c.isalnum())
            if key_norm in msg_norm:
                found_keys.append(key)
                
        is_route_query = any(w in normalized_msg for w in ["route", "get to", "go from", "directions", "how to", "how do i", "map", "llego", "ruta", "ir de", "ir a", "cómo"])
        
        if is_route_query and len(found_keys) > 0:
            accessibility_required = any(w in normalized_msg for w in ["wheelchair", "accessible", "disabled", "ramp", "elevator", "stroller", "silla de ruedas", "acceso", "rampa", "ascensor"])
            
            from_location = "Gate 1"
            to_location = locations[found_keys[0]]
            
            if len(found_keys) >= 2:
                idx0 = normalized_msg.find(found_keys[0])
                idx1 = normalized_msg.find(found_keys[1])
                if idx0 < idx1:
                    from_location = locations[found_keys[0]]
                    to_location = locations[found_keys[1]]
                else:
                    from_location = locations[found_keys[1]]
                    to_location = locations[found_keys[0]]
            elif len(found_keys) == 1:
                matched = locations[found_keys[0]]
                if matched == "Gate 1":
                    from_location = "Gate 2"
                    to_location = "Gate 1"
                else:
                    from_location = "Gate 1"
                    to_location = matched
                    
            tool_calls.append(ToolCall("get_route", {
                "from_location": from_location,
                "to_location": to_location,
                "accessibility_required": accessibility_required
            }))
            
            if is_spanish:
                reply = f"He trazado una ruta accesible de {from_location} a {to_location}. He cargado la ruta accesible en el mapa interactivo."
            else:
                reply = f"Sure! I have generated a {'step-free accessible ' if accessibility_required else 'standard '}route from {from_location} to {to_location}. I've highlighted the path on your map."

        # 2. Check for Gate Status Queries
        elif "gate" in normalized_msg and any(w in normalized_msg for w in ["status", "open", "closed", "state"]) and not any(w in normalized_msg for w in ["hour", "time", "when", "restriction", "policy"]):
            tool_calls.append(ToolCall("get_gate_status", {}))
            if "gate 2" in normalized_msg:
                reply = "Here is the status of the gates: Gate 2 (East) is open."
            else:
                reply = "Here is the status of the gates."

        # 3. Check for Crowd Density Queries
        elif any(w in normalized_msg for w in ["density", "crowd", "capacity", "congest", "gente", "personas", "tráfico", "trafico"]):
            zones = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-VIP"]
            target_zone = "Zone-C"
            for z in zones:
                if z.lower() in normalized_msg:
                    target_zone = z
            
            tool_calls.append(ToolCall("get_crowd_density", {"zone": target_zone}))
            if "staff" in system_prompt.lower() or "operational" in system_prompt.lower():
                reply = f"[STAFF OPERATIONAL BRIEF] Zone {target_zone} (South Concourse C) is at 90% capacity. Congestion status is active."
            else:
                reply = f"The crowd level in South Concourse C is currently at 90% capacity."

        # 4. Specific hello / ping cases
        elif "ping" in normalized_msg:
            reply = "pong"

        # 5. Fallback: Dynamic RAG Search using local facts database
        else:
            try:
                from backend.app.rag import get_rag
                rag = get_rag()
                rag_results = rag.retrieve(user_message, top_k=1)
                if rag_results and rag_results[0]["similarity"] > 0:
                    best_match = rag_results[0]
                    if is_spanish:
                        if "baños" in normalized_msg or "banos" in normalized_msg:
                            reply = "Los baños accesibles están en todos los niveles cerca de las secciones 104, 112, 205, 220, 304 y 318."
                        elif "halal" in normalized_msg or "vegetariana" in normalized_msg:
                            reply = "De acuerdo a la información del estadio: Concourse A features certified Halal food stalls at Section 105."
                        else:
                            reply = f"De acuerdo a la información del estadio: {best_match['content']}"
                    else:
                        reply = f"According to stadium guidelines: {best_match['content']}"
                else:
                    reply = "Welcome to EktaAI, your stadium assistant. How can I help you navigate the stadium or find facilities today?"
            except Exception as e:
                logger.error(f"Dynamic RAG search failed: {e}")
                reply = "Welcome to EktaAI, your stadium assistant. How can I help you navigate the stadium or find facilities today?"

        return LLMResult(reply=reply, tool_calls=tool_calls)

    def generate_stream(self, system_prompt: str, user_message: str, tools: list = None, response_format: dict = None, mode: str = None, history: list = None):
        logger.info("Executing MockLLMClient generate_stream.")
        res = self.generate(system_prompt, user_message, tools, response_format, mode, history=history)
        
        # Stream tool calls if present
        if res.tool_calls:
            tool_calls_list = []
            for idx, tc in enumerate(res.tool_calls):
                tool_calls_list.append({
                    "index": idx,
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.args)
                    }
                })
            yield {"tool_calls": tool_calls_list}
            return
            
        # Stream content if present
        if res.reply:
            # Yield tokens with minimal sleep to simulate network speed
            words = res.reply.split(" ")
            for idx, word in enumerate(words):
                space = " " if idx > 0 else ""
                yield {"content": space + word}

class GroqLLMClient:
    provider_name = "groq"
    def __init__(self, api_key: str):
        self.api_key = api_key
        from backend.app.config import Config
        self.model = Config.GROQ_MODEL
        logger.info(f"GroqLLMClient initialized using model {self.model}.")

    def get_openai_tools(self) -> list:
        return [
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
                                "description": "Start point (e.g., 'Gate 1', 'Gate 2')"
                            },
                            "to_location": {
                                "type": "string",
                                "description": "Destination point (e.g., 'Section 102', 'Section 204')"
                            },
                            "accessibility_required": {
                                "type": "boolean",
                                "description": "True if step-free accessible route is needed."
                            }
                        },
                        "required": ["from_location", "to_location"]
                    }
                }
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
                                "description": "The zone ID (e.g. 'Zone-A', 'Zone-B', 'Zone-C') or zone name."
                            }
                        },
                        "required": ["zone"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_gate_status",
                    "description": "Gets the status (open/closed) and congestion level of all stadium gates.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

    def _build_messages(self, system_prompt: str, user_message: str, history: list = None) -> list:
        full_history = []
        if history:
            for msg in history:
                if isinstance(msg, dict):
                    role = msg.get("role")
                    content = msg.get("content")
                elif hasattr(msg, "role") and hasattr(msg, "content"):
                    role = msg.role
                    content = msg.content
                else:
                    continue
                
                if role and content:
                    role_norm = "assistant" if role in ["bot", "assistant"] else "user"
                    full_history.append({"role": role_norm, "content": content})
                    
        full_history.append({"role": "user", "content": user_message})
        
        # Slice/truncate to max of last 4 messages to keep payload lightweight and avoid token limits
        recent_history = full_history[-4:]
        
        return [{"role": "system", "content": system_prompt}] + recent_history

    def generate(self, system_prompt: str, user_message: str, tools: list = None, response_format: dict = None, mode: str = None, history: list = None) -> LLMResult:
        logger.info(f"Executing Groq API call via httpx to model {self.model}.")
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_message, history),
            "temperature": 0.1,
            "max_tokens": 150 # Strict completion cap
        }
        
        if response_format:
            payload["response_format"] = response_format
            
        if tools:
            payload["tools"] = self.get_openai_tools()
            payload["tool_choice"] = "auto"
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                res_data = response.json()
                
            choice = res_data["choices"][0]["message"]
            reply = choice.get("content") or ""
            raw_tool_calls = choice.get("tool_calls") or []
            
            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                name = func.get("name")
                args_str = func.get("arguments") or "{}"
                try:
                    args = json.loads(args_str)
                except Exception:
                    args = {}
                # Models may return "null" or a non-object for no-arg tools; coerce to {}
                # so tool_fn(**args) never receives None.
                if not isinstance(args, dict):
                    args = {}
                tool_calls.append(ToolCall(name=name, args=args))
                
            return LLMResult(reply=reply, tool_calls=tool_calls)
            
        except Exception as e:
            logger.error(f"Groq API HTTP Request failed: {e}")
            raise e

    def generate_stream(self, system_prompt: str, user_message: str, tools: list = None, response_format: dict = None, history: list = None):
        logger.info(f"Executing Groq streaming API call via httpx to model {self.model}.")
        import httpx
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": self._build_messages(system_prompt, user_message, history),
            "temperature": 0.1,
            "max_tokens": 150, # Enforce strict max_tokens cap
            "stream": True
        }
        
        if response_format:
            payload["response_format"] = response_format
            
        if tools:
            payload["tools"] = self.get_openai_tools()
            payload["tool_choice"] = "auto"
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        try:
            with httpx.Client(timeout=15.0) as client:
                with client.stream("POST", url, headers=headers, json=payload) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line.startswith("data: "):
                            data_str = line[len("data: "):]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choice = chunk["choices"][0]
                                delta = choice.get("delta", {})
                                yield delta
                            except Exception:
                                continue
        except Exception as e:
            logger.error(f"Groq stream request failed: {e}")
            raise e
