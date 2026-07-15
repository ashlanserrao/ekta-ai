import os
from pathlib import Path
from dotenv import load_dotenv

# Base workspace directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from root .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

class Config:
    # NOTE: os.getenv(key, default) only falls back when the var is UNSET.
    # If .env defines "DATABASE_PATH=" (empty), os.getenv returns "" and the
    # default is silently skipped. We guard against that here with `or default`.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or ""
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "") or ""
    GROQ_MODEL = os.getenv("GROQ_MODEL", "") or "llama-3.3-70b-versatile"
    DATABASE_PATH = os.getenv("DATABASE_PATH", "") or str(BASE_DIR / "stadium_twin.db")
    STADIUM_FACTS_PATH = os.getenv("STADIUM_FACTS_PATH", "") or str(BASE_DIR / "backend" / "data" / "stadium_facts.json")

    # Rate limit settings
    RATE_LIMIT_LIMIT = int(os.getenv("RATE_LIMIT_LIMIT", "") or "5")
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "") or "10")  # seconds

    # Security
    ALLOWED_ORIGINS = (os.getenv("ALLOWED_ORIGINS", "") or "http://localhost:5173").split(",")
