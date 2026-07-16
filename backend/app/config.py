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
    GROQ_EXHAUSTED: bool = Field(default=False)

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

    def is_exhausted(self, provider: str) -> bool:
        """Thread-safe check to verify if a provider is rate limited/exhausted."""
        with self._cb_lock:
            if provider == "groq":
                return self.GROQ_EXHAUSTED
            return False

    def set_exhausted(self, provider: str, value: bool = True):
        """Thread-safe update of the exhaustion state of a provider."""
        with self._cb_lock:
            if provider == "groq":
                self.GROQ_EXHAUSTED = value

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
Config = settings
