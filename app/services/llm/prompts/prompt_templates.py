"""Prompt templates for Stage 1/2 generation."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_MARKDOWN = ROOT / "Prompt 模板清单.md"


def load_raw_markdown() -> str:
    return RAW_MARKDOWN.read_text(encoding="utf-8")
