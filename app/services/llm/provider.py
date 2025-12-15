"""Unified LLM provider wrapper for any OpenAI-compatible API.

This module provides a single interface for calling various LLM APIs including:
- OpenAI (api.openai.com)
- DeepSeek (api.deepseek.com)
- Azure OpenAI
- Custom OpenAI-compatible endpoints
- Local models (via OpenAI-compatible gateways)

All configuration is done via environment variables for flexibility.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional

import requests

from app.core.config import get_settings


class LLMClient:
    """Universal OpenAI-compatible LLM client.

    This client works with any API that follows the OpenAI chat completions format.
    Simply set the appropriate environment variables to switch between providers.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """Initialize LLM client.

        Args:
            api_key: API key. If None, reads from environment (LLM_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY).
            base_url: API base URL. If None, reads from environment (LLM_BASE_URL, OPENAI_BASE_URL, or DEEPSEEK_BASE_URL).
            model: Model name. If None, reads from environment (LLM_MODEL, OPENAI_MODEL, or DEEPSEEK_MODEL).
            max_tokens: Maximum tokens. If None, reads from environment (LLM_MAX_TOKENS, default: 4000).
            temperature: Sampling temperature. If None, reads from environment (LLM_TEMPERATURE, default: 0.7).
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

        # Ensure base_url ends with /v1 for OpenAI compatibility
        if not self.base_url.endswith("/v1"):
            self.base_url = self.base_url.rstrip("/") + "/v1"

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        print(f"🤖 LLM Client initialized:")
        print(f"   Provider: {self._get_provider_name()}")
        print(f"   Base URL: {self.base_url}")
        print(f"   Model: {self.model}")
        print(f"   Max Tokens: {self.max_tokens}")
        print(f"   Temperature: {self.temperature}")

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
    ) -> Dict[str, Any] | Generator[str, None, None]:
        """Complete a prompt using the configured LLM API.

        Args:
            prompt: The prompt to send
            model: Model name (defaults to configured model)
            max_tokens: Maximum tokens (defaults to configured max_tokens)
            temperature: Sampling temperature (defaults to configured temperature)
            stream: Whether to stream response

        Returns:
            Response dict or generator if stream=True
        """
        data = {
            "model": model or self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "stream": stream
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                stream=stream,
                timeout=300
            )

            if not stream:
                return self._handle_response(response)
            else:
                return self._handle_stream_response(response)

        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle non-streaming response."""
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            raise RuntimeError(f"API request failed: {error_msg}")

        result = response.json()

        if "error" in result:
            raise RuntimeError(f"API error: {result['error']}")

        return {
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {}),
            "model": result.get("model", ""),
            "finish_reason": result["choices"][0].get("finish_reason", "")
        }

    def _handle_stream_response(self, response: requests.Response) -> Generator[str, None, None]:
        """Handle streaming response."""
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            raise RuntimeError(f"API request failed: {error_msg}")

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode('utf-8')
            if line.startswith('data: '):
                line = line[6:]

                if line.strip() == '[DONE]':
                    break

                try:
                    data = json.loads(line)
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                except json.JSONDecodeError:
                    continue

    def batch_complete(
        self,
        prompts: List[str],
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> List[Dict[str, Any]]:
        """Complete multiple prompts in batch.

        Args:
            prompts: List of prompts to process
            model: Model name (defaults to configured model)
            max_tokens: Maximum tokens (defaults to configured max_tokens)
            temperature: Sampling temperature (defaults to configured temperature)

        Returns:
            List of response dicts
        """
        results = []
        for i, prompt in enumerate(prompts):
            print(f"Processing prompt {i+1}/{len(prompts)}...")
            try:
                result = self.complete(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=False
                )
                results.append(result)
            except Exception as e:
                print(f"Warning: Failed to process prompt {i+1}: {e}")
                results.append({"error": str(e)})

        return results


# Convenience functions for easy use
def call_model(
    prompt: str,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    stream: bool = False,
) -> Dict[str, Any] | Generator[str, None, None]:
    """Call the LLM with a prompt and return parsed response.

    This is the main entry point for LLM calls.
    Uses the configured provider from environment variables.

    Args:
        prompt: The prompt to send
        model: Model name (optional, uses default from config)
        max_tokens: Max tokens (optional, uses default from config)
        temperature: Temperature (optional, uses default from config)
        stream: Whether to stream response

    Returns:
        Response dict or generator if stream=True
    """
    client = LLMClient()
    return client.complete(
        prompt=prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=stream
    )


def batch_call_model(
    prompts: List[str],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> List[Dict[str, Any]]:
    """Call the LLM with multiple prompts.

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


# Backward compatibility aliases
DeepSeekProvider = LLMClient  # Alias for backward compatibility

