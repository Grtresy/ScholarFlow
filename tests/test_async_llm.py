"""Tests for async LLM provider using LangChain."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm.provider import (
    LLMClient,
    call_model,
    acall_model,
    batch_call_model,
    abatch_call_model,
)


class TestAsyncLLMClient:
    """Test async LLM client functionality."""

    def test_init(self):
        """Test LLM client initialization."""
        client = LLMClient(
            api_key="test_key",
            base_url="https://api.test.com",
            model="test_model",
            max_tokens=1000,
            temperature=0.5,
        )

        assert client.api_key == "test_key"
        assert client.base_url == "https://api.test.com/v1"
        assert client.model == "test_model"
        assert client.max_tokens == 1000
        assert client.temperature == 0.5

    @pytest.mark.asyncio
    async def test_acomplete(self):
        """Test async LLM completion."""
        # Mock the LangChain client
        with patch('app.services.llm.provider.ChatOpenAI') as mock_openai:
            mock_response = MagicMock()
            mock_response.content = "Test response"
            mock_response.usage_metadata = {"total_tokens": 100}

            mock_client = AsyncMock()
            mock_client.ainvoke.return_value = mock_response
            mock_openai.return_value = mock_client

            client = LLMClient(api_key="test_key")
            response = await client.acomplete(prompt="Test prompt")

            assert response["content"] == "Test response"
            assert response["usage"]["total_tokens"] == 100
            # Don't check specific model name, just ensure it exists
            assert "model" in response
            assert response["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_abatch_complete(self):
        """Test async batch LLM completion."""
        with patch('app.services.llm.provider.ChatOpenAI') as mock_openai:
            mock_response1 = MagicMock()
            mock_response1.content = "Response 1"

            mock_response2 = MagicMock()
            mock_response2.content = "Response 2"

            mock_client = AsyncMock()
            mock_client.abatch.return_value = [mock_response1, mock_response2]
            mock_openai.return_value = mock_client

            client = LLMClient(api_key="test_key")
            responses = await client.abatch_complete(prompts=["Prompt 1", "Prompt 2"])

            assert len(responses) == 2
            assert responses[0]["content"] == "Response 1"
            assert responses[1]["content"] == "Response 2"

    @pytest.mark.asyncio
    async def test_astream(self):
        """Test async streaming response."""
        with patch('app.services.llm.provider.ChatOpenAI') as mock_openai:
            # Define generator function - simulate real LangChain objects
            async def mock_gen(*args, **kwargs):
                chunk1 = MagicMock()
                chunk1.content = "Chunk 1"
                yield chunk1

                chunk2 = MagicMock()
                chunk2.content = "Chunk 2"
                yield chunk2

            mock_client = AsyncMock()
            # --- 关键修复: MagicMock with side_effect ---
            # 确保返回生成器对象，而不是协程
            mock_client.astream = MagicMock(side_effect=mock_gen)
            mock_openai.return_value = mock_client

            client = LLMClient(api_key="test_key")
            chunks = []
            async for chunk in client.astream(prompt="Test prompt"):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == "Chunk 1"
            assert chunks[1] == "Chunk 2"

    def test_provider_name_detection(self):
        """Test provider name detection from base URL."""
        client = LLMClient(api_key="test", base_url="https://api.deepseek.com")
        assert client._get_provider_name() == "DeepSeek"

        client = LLMClient(api_key="test", base_url="https://api.openai.com")
        assert client._get_provider_name() == "OpenAI"

        client = LLMClient(api_key="test", base_url="https://custom.api.com")
        assert client._get_provider_name() == "Custom OpenAI-Compatible"


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_acall_model(self):
        """Test async call_model convenience function."""
        with patch('app.services.llm.provider.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.acomplete.return_value = {
                "content": "Test",
                "usage": {},
                "model": "test",
                "finish_reason": "stop"
            }
            mock_client_class.return_value = mock_client

            response = await acall_model(prompt="Test prompt")

            assert response["content"] == "Test"
            mock_client.acomplete.assert_called_once()

    @pytest.mark.asyncio
    async def test_abatch_call_model(self):
        """Test async batch_call_model convenience function."""
        with patch('app.services.llm.provider.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.abatch_complete.return_value = [
                {"content": "Response 1"},
                {"content": "Response 2"}
            ]
            mock_client_class.return_value = mock_client

            responses = await abatch_call_model(prompts=["Prompt 1", "Prompt 2"])

            assert len(responses) == 2
            assert responses[0]["content"] == "Response 1"
            assert responses[1]["content"] == "Response 2"
            mock_client.abatch_complete.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
