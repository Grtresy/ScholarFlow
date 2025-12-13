"""Centralized configuration loading.

Env vars are preferred; extend as needed for secrets/providers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    deepseek_api_key: str | None
    deepseek_base_url: str | None
    mineru_endpoint: str | None
    oss_endpoint: str | None
    oss_bucket: str | None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL"),
        mineru_endpoint=os.getenv("MINERU_ENDPOINT"),
        oss_endpoint=os.getenv("OSS_ENDPOINT"),
        oss_bucket=os.getenv("OSS_BUCKET"),
    )
