from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Any
import threading

# Base workspace directory (h:\PromptWars)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENV: str = Field(default="development")
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")
    DATABASE_PATH: str = Field(default="")
    STADIUM_FACTS_PATH: str = Field(default="")
    
    # Circuit breaker flags (mutable)
    groq_cooldown_until: float = Field(default=0.0)

    # Rate limit settings
    RATE_LIMIT_LIMIT: int = Field(default=5)
    RATE_LIMIT_WINDOW: int = Field(default=10)

    # Security
    ALLOWED_ORIGINS: Any = Field(default="http://localhost:5173")
    STAFF_PASSCODE: str = Field(default="fifa2026")
    JWT_SECRET: str = Field(default="supersecretjwtkey")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Bypasses Pydantic setattr interception to prevent validation errors on private lock field
        object.__setattr__(self, "_cb_lock", threading.Lock())
        self._validate_production_secrets()

    # Known-insecure placeholder values that must never reach production
    _WEAK_SECRETS = {
        "",
        "supersecretjwtkey",
        "change-me",
        "change-me-to-a-random-64-char-hex-string",
    }

    def _validate_production_secrets(self):
        """In production, refuse to boot with weak/default auth secrets.
        Set these via environment variables (e.g. docker run --env-file .env)."""
        if self.ENV != "production":
            return
        if self.JWT_SECRET in self._WEAK_SECRETS or len(self.JWT_SECRET) < 32:
            raise ValueError(
                "Refusing to start in production with a weak or default JWT_SECRET. "
                "Provide a strong 32+ byte secret via the JWT_SECRET environment variable "
                '(generate one with: python -c "import secrets; print(secrets.token_hex(32))").'
            )
        if self.STAFF_PASSCODE in self._WEAK_SECRETS or self.STAFF_PASSCODE == "fifa2026":
            raise ValueError(
                "Refusing to start in production with the default STAFF_PASSCODE. "
                "Set a private STAFF_PASSCODE via environment variable."
            )

    def is_exhausted(self, provider: str) -> bool:
        """Thread-safe check to verify if a provider is rate limited/exhausted."""
        with self._cb_lock:
            if provider == "groq":
                import time
                return time.time() < self.groq_cooldown_until
            return False

    def set_exhausted(self, provider: str, value: bool = True):
        """Thread-safe update of the exhaustion state of a provider."""
        with self._cb_lock:
            if provider == "groq":
                import time
                self.groq_cooldown_until = time.time() + 60.0 if value else 0.0

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:5173"]

    @field_validator("DATABASE_PATH", mode="after")
    @classmethod
    def default_database_path(cls, v: str) -> str:
        if not v:
            return str(BASE_DIR / "stadium_twin.db")
        return v

    @field_validator("STADIUM_FACTS_PATH", mode="after")
    @classmethod
    def default_stadium_facts_path(cls, v: str) -> str:
        if not v:
            return str(BASE_DIR / "backend" / "data" / "stadium_facts.json")
        return v

settings = Settings()
