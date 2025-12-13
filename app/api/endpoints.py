"""API endpoints placeholder (FastAPI/Flask)."""
from __future__ import annotations

from typing import Any, Dict, List


def upload(pdf_bytes: bytes) -> Dict[str, Any]:
    raise NotImplementedError


def generate_outline(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    raise NotImplementedError


def render(outline_md: str) -> bytes:
    raise NotImplementedError
