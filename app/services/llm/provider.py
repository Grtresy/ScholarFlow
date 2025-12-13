"""LLM provider wrapper (DeepSeek/OpenAI compatible)."""
from __future__ import annotations

from typing import Any, Dict


def call_model(prompt: str, model: str = "deepseek-chat") -> Dict[str, Any]:
    """Call the LLM with a prompt and return parsed response.

    Replace with actual SDK invocation; keep interface minimal for swapping backends.
    """
    raise NotImplementedError("Integrate DeepSeek/OpenAI client here")
