import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.llm_client import GroqLLMClient

def test_fan_chat_history_payload():
    from backend.app.middleware.rate_limit import chat_limiter
    chat_limiter.request_timestamps.clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/chat/fan",
            json={
                "message": "And accessibility options?",
                "language": "en",
                "history": [
                    {"role": "user", "content": "How do I get to Section 105?"},
                    {"role": "assistant", "content": "Use the North Concourse Ramp."}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data

def test_groq_client_history_building():
    client = GroqLLMClient(api_key="mock_key")
    
    history = [
        {"role": "user", "content": "Msg 1"},
        {"role": "assistant", "content": "Msg 2"},
        {"role": "user", "content": "Msg 3"},
        {"role": "assistant", "content": "Msg 4"},
        {"role": "user", "content": "Msg 5"}
    ]
    
    messages = client._build_messages(
        system_prompt="System prompt",
        user_message="Msg 6",
        history=history
    )
    
    assert len(messages) == 5
    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "Msg 3"
    assert messages[2]["content"] == "Msg 4"
    assert messages[3]["content"] == "Msg 5"
    assert messages[4]["content"] == "Msg 6"
