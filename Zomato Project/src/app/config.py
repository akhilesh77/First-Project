"""Application configuration from environment variables."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "restaurants.db"
DEFAULT_HF_DATASET = "ManikaSaini/zomato-restaurant-recommendation"


def _resolve_sqlite_path(database_url: str) -> Path:
    """Parse sqlite:///path into a filesystem Path."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(
            f"Only SQLite URLs are supported in Phase 1 (got {database_url!r}). "
            "Use sqlite:///data/restaurants.db"
        )
    raw = database_url[len(prefix) :]
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def get_database_path() -> Path:
    url = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH.relative_to(PROJECT_ROOT)}")
    return _resolve_sqlite_path(url)


def get_hf_dataset_id() -> str:
    return os.getenv("HF_DATASET", DEFAULT_HF_DATASET)


def get_max_candidates() -> int:
    """Max restaurants passed to LLM after filter (Phase 2 cap)."""
    raw = os.getenv("N_MAX_CANDIDATES", "30")
    value = int(raw)
    if value < 1:
        raise ValueError("N_MAX_CANDIDATES must be at least 1")
    return value


def get_default_top_k() -> int:
    raw = os.getenv("TOP_K_DEFAULT", "5")
    value = int(raw)
    if value < 1:
        raise ValueError("TOP_K_DEFAULT must be at least 1")
    return value


def get_max_top_k() -> int:
    raw = os.getenv("TOP_K_MAX", "20")
    value = int(raw)
    if value < 1:
        raise ValueError("TOP_K_MAX must be at least 1")
    return value


def get_max_additional_preferences_length() -> int:
    return int(os.getenv("MAX_ADDITIONAL_PREFERENCES_LENGTH", "500"))


def get_api_key() -> Optional[str]:
    """If set, requests must include matching X-API-Key header."""
    key = os.getenv("API_KEY", "").strip()
    return key or None


def get_cors_origins() -> List[str]:
    # Support both CORS_ORIGINS and CORS_ALLOWED_ORIGINS (commonly configured for Vercel frontends)
    raw = os.getenv("CORS_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGINS") or "*"
    if raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


# --- Groq LLM (Phase 4) ---

DEFAULT_LLM_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"


def get_llm_api_key() -> Optional[str]:
    """Groq API key (GROQ_API_KEY preferred, LLM_API_KEY fallback)."""
    return (os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or "").strip() or None


def get_llm_base_url() -> str:
    return os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip()


def get_llm_model() -> str:
    """LLM model id (e.g. llama-3.3-70b-versatile)."""
    return os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL).strip()


def get_llm_timeout_seconds() -> float:
    return float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))


def get_llm_temperature() -> float:
    return float(os.getenv("LLM_TEMPERATURE", "0.2"))


def get_llm_max_tokens() -> int:
    return int(os.getenv("LLM_MAX_TOKENS", "2048"))


def is_llm_enabled() -> bool:
    """Use LLM when enabled and API key is configured."""
    flag = os.getenv("LLM_ENABLED", "true").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    return get_llm_api_key() is not None
