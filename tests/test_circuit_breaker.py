import time
import pytest
from backend.app.config import settings
from backend.app.services.orchestrator import is_quota_or_rate_limit_error

def test_circuit_breaker_cooldown():
    # Ensure starting in non-exhausted state
    settings.set_exhausted("groq", False)
    assert settings.is_exhausted("groq") is False

    # Trip the circuit breaker
    settings.set_exhausted("groq", True)
    assert settings.is_exhausted("groq") is True

    # Manually speed up time by mutating the cooldown timestamp
    settings.groq_cooldown_until = time.time() - 1.0
    # Circuit breaker should now not be active (cooldown expired)
    assert settings.is_exhausted("groq") is False

def test_error_detection_403_and_429():
    assert is_quota_or_rate_limit_error("Client error 429 Too Many Requests") is True
    assert is_quota_or_rate_limit_error("Client error 403 Forbidden") is True
    assert is_quota_or_rate_limit_error("Some connection timeout") is False
