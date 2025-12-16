"""Centralized configuration loading.

Env vars are preferred; extend as needed for secrets/providers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env from project root
    project_root = Path(__file__).resolve().parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    # python-dotenv not installed, skip
    pass


@dataclass
class Settings:
    # LLM Provider Configuration (OpenAI-compatible)
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_max_tokens: int = 4000
    llm_temperature: float = 0.7

    # MinerU Configuration
    mineru_api_key: str | None = None
    mineru_endpoint: str | None = None

    # Storage Configuration
    storage_backend: str = "local"  # 'local', 's3', etc.

    # Data Directory
    data_dir: Path | None = None

    # MariaDB Configuration for Workflow State Persistence
    mariadb_host: str = "localhost"
    mariadb_port: int = 3306
    mariadb_user: str = "scholarflow"
    mariadb_password: str = ""
    mariadb_db: str = "scholarflow_state"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        # LLM Configuration - supports any OpenAI-compatible API
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        llm_model=os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4000")),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),

        # MinerU Configuration
        mineru_api_key=os.getenv("MINERU_API_KEY"),
        mineru_endpoint=os.getenv("MINERU_ENDPOINT"),

        # Storage Configuration
        storage_backend=os.getenv("STORAGE_BACKEND", "local"),

        # Data Directory
        data_dir=Path(os.getenv("DATA_DIR", "data")) if os.getenv("DATA_DIR") else None,

        # MariaDB Configuration for Workflow State Persistence
        mariadb_host=os.getenv("MARIA_DB_HOST", "localhost"),
        mariadb_port=int(os.getenv("MARIA_DB_PORT", "3306")),
        mariadb_user=os.getenv("MARIA_DB_USER", "scholarflow"),
        mariadb_password=os.getenv("MARIA_DB_PASSWORD", ""),
        mariadb_db=os.getenv("MARIA_DB_NAME", "scholarflow_state"),
    )
