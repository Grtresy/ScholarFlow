"""Unified LLM provider wrapper using LangChain for async operations.

This module provides both synchronous and asynchronous interfaces using LangChain:
- OpenAI (api.openai.com)
- DeepSeek (api.deepseek.com)
- Azure OpenAI
- Custom OpenAI-compatible endpoints
- Local models (via OpenAI-compatible gateways)

LangChain provides:
- Native async support (acall, abatch)
- Connection pooling and HTTP/2
- Built-in retry and error handling
- Streaming support
- Better integration with LangGraph

All configuration is done via environment variables for flexibility.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, AsyncGenerator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.core.config import get_settings


class LLMClient:
    """Universal OpenAI-compatible LLM client using LangChain.

    This client works with any API that follows the OpenAI chat completions format.
    Simply set the appropriate environment variables to switch between providers.

    Provides both sync and async interfaces via LangChain.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: float = 300.0,
    ):
        """Initialize LLM client using LangChain.

        Args:
            api_key: API key. If None, reads from environment (LLM_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY).
            base_url: API base URL. If None, reads from environment (LLM_BASE_URL, OPENAI_BASE_URL, or DEEPSEEK_BASE_URL).
            model: Model name. If None, reads from environment (LLM_MODEL, OPENAI_MODEL, or DEEPSEEK_MODEL).
            max_tokens: Maximum tokens. If None, reads from environment (LLM_MAX_TOKENS, default: 4000).
            temperature: Sampling temperature. If None, reads from environment (LLM_TEMPERATURE, default: 0.7).
            timeout: Request timeout in seconds (default: 300).
        """
        settings = get_settings()

        # Configuration with fallbacks
        self.api_key = api_key or settings.llm_api_key
        if not self.api_key:
            raise ValueError(
                "LLM API key is required. Set one of: LLM_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY"
            )

        self.base_url = base_url or settings.llm_base_url or "https://api.deepseek.com"
        self.model = model or settings.llm_model or "deepseek-chat"
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.temperature = temperature or settings.llm_temperature
        self.timeout = timeout

        # Ensure base_url ends with /v1 for OpenAI compatibility
        if not self.base_url.endswith("/v1"):
            self.base_url = self.base_url.rstrip("/") + "/v1"

        # Initialize LangChain ChatOpenAI client
        self._client = ChatOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            request_timeout=self.timeout,
            max_retries=3,
        )

        print(f"🤖 LangChain LLM Client initialized:")
        print(f"   Provider: {self._get_provider_name()}")
        print(f"   Base URL: {self.base_url}")
        print(f"   Model: {self.model}")
        print(f"   Max Tokens: {self.max_tokens}")
        print(f"   Temperature: {self.temperature}")
        print(f"   Timeout: {self.timeout}s")

    def _get_provider_name(self) -> str:
        """Get the name of the LLM provider based on the base URL."""
        url = self.base_url.lower()
        if "deepseek" in url:
            return "DeepSeek"
        elif "openai" in url and "azure" not in url:
            return "OpenAI"
        elif "azure" in url:
            return "Azure OpenAI"
        else:
            return "Custom OpenAI-Compatible"

    def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Complete a prompt using LangChain (synchronous).

        Args:
            prompt: The prompt to send
            model: Model name (defaults to configured model)
            max_tokens: Maximum tokens (defaults to configured max_tokens)
            temperature: Sampling temperature (defaults to configured temperature)
            stream: Whether to stream response

        Returns:
            Response dict with content and metadata
        """
        # Note: LangChain's ChatOpenAI doesn't support stream in this interface
        # Use astream for streaming
        try:
            response = self._client.invoke([HumanMessage(content=prompt)])

            return {
                "content": response.content,
                "usage": getattr(response, "usage_metadata", {}),
                "model": self.model,
                "finish_reason": "stop"
            }

        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

    async def acomplete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Dict[str, Any]:
        """Complete a prompt using LangChain (asynchronous).

        Args:
            prompt: The prompt to send
            model: Model name (defaults to configured model)
            max_tokens: Maximum tokens (defaults to configured max_tokens)
            temperature: Sampling temperature (defaults to configured temperature)

        Returns:
            Response dict with content and metadata
        """
        try:
            response = await self._client.ainvoke([HumanMessage(content=prompt)])

            return {
                "content": response.content,
                "usage": getattr(response, "usage_metadata", {}),
                "model": self.model,
                "finish_reason": "stop"
            }

        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

    async def astream(
        self,
        prompt: str,
    ) -> AsyncGenerator[str, None, None]:
        """Stream response from LLM using LangChain.

        Args:
            prompt: The prompt to send

        Yields:
            Chunks of response content
        """
        try:
            # LangChain's astream is async, so we need to await it first
            stream = self._client.astream([HumanMessage(content=prompt)])
            async for chunk in stream:
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content

        except Exception as e:
            raise RuntimeError(f"LLM streaming failed: {e}")

    def batch_complete(
        self,
        prompts: List[str],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> List[Dict[str, Any]]:
        """Complete multiple prompts in batch (synchronous).

        Args:
            prompts: List of prompts to process
            model: Model name (defaults to configured model)
            max_tokens: Maximum tokens (defaults to configured max_tokens)
            temperature: Sampling temperature (defaults to configured temperature)

        Returns:
            List of response dicts
        """
        try:
            # Use LangChain's batch processing
            messages_list = [[HumanMessage(content=prompt)] for prompt in prompts]
            responses = self._client.batch(messages_list)

            return [
                {
                    "content": response.content,
                    "usage": getattr(response, "usage_metadata", {}),
                    "model": self.model,
                    "finish_reason": "stop"
                }
                for response in responses
            ]

        except Exception as e:
            raise RuntimeError(f"Batch LLM call failed: {e}")

    async def abatch_complete(
        self,
        prompts: List[str],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> List[Dict[str, Any]]:
        """Complete multiple prompts in batch (asynchronous, concurrent).

        Args:
            prompts: List of prompts to process
            model: Model name (defaults to configured model)
            max_tokens: Maximum tokens (defaults to configured max_tokens)
            temperature: Sampling temperature (defaults to configured temperature)

        Returns:
            List of response dicts
        """
        try:
            # Use LangChain's async batch processing with concurrency
            messages_list = [[HumanMessage(content=prompt)] for prompt in prompts]
            responses = await self._client.abatch(messages_list)

            return [
                {
                    "content": response.content,
                    "usage": getattr(response, "usage_metadata", {}),
                    "model": self.model,
                    "finish_reason": "stop"
                }
                for response in responses
            ]

        except Exception as e:
            raise RuntimeError(f"Async batch LLM call failed: {e}")


# Convenience functions for easy use
def call_model(
    prompt: str,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """Call the LLM with a prompt and return parsed response (synchronous).

    This is the main entry point for synchronous LLM calls.
    Uses the configured provider from environment variables.

    Args:
        prompt: The prompt to send
        model: Model name (optional, uses default from config)
        max_tokens: Max tokens (optional, uses default from config)
        temperature: Temperature (optional, uses default from config)
        stream: Whether to stream response (note: use astream for async streaming)

    Returns:
        Response dict
    """
    client = LLMClient()
    return client.complete(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream
    )


async def acall_model(
    prompt: str,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Dict[str, Any]:
    """Call the LLM with a prompt and return parsed response (asynchronous).

    This is the main entry point for asynchronous LLM calls.
    Uses the configured provider from environment variables.

    Args:
        prompt: The prompt to send
        model: Model name (optional, uses default from config)
        max_tokens: Max tokens (optional, uses default from config)
        temperature: Temperature (optional, uses default from config)

    Returns:
        Response dict
    """
    client = LLMClient()
    return await client.acomplete(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )


def batch_call_model(
    prompts: List[str],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> List[Dict[str, Any]]:
    """Call the LLM with multiple prompts (synchronous batch).

    Args:
        prompts: List of prompts to process
        model: Model name (optional)
        max_tokens: Max tokens (optional)
        temperature: Temperature (optional)

    Returns:
        List of response dicts
    """
    client = LLMClient()
    return client.batch_complete(
        prompts=prompts,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )


async def abatch_call_model(
    prompts: List[str],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> List[Dict[str, Any]]:
    """Call the LLM with multiple prompts (asynchronous concurrent batch).

    Args:
        prompts: List of prompts to process
        model: Model name (optional)
        max_tokens: Max tokens (optional)
        temperature: Temperature (optional)

    Returns:
        List of response dicts
    """
    client = LLMClient()
    return await client.abatch_complete(
        prompts=prompts,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )


# Backward compatibility aliases
DeepSeekProvider = LLMClient  # Alias for backward compatibility
