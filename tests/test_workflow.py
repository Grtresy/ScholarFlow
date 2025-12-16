"""Tests for workflow orchestration using LangGraph."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from app.graph.state import TaskStatus, WorkflowState
from app.graph.nodes.stage1_processing import node_stage1_process, should_continue_stage1
from app.graph.nodes.stage2_processing import node_stage2_process
from app.graph.nodes.outline_merging import node_merge_outlines
from app.graph.nodes.pdf_parsing import node_parse_pdf
from app.graph.nodes.rendering import node_render


class TestStage1Processing:
    """Test Stage 1 processing node."""

    @pytest.mark.asyncio
    async def test_stage1_process_all_chunks_completed(self):
        """Test when all chunks are processed."""
        state = {
            "chunks": [
                {"id": 1, "title": "Chunk 1", "text": "Text 1"},
                {"id": 2, "title": "Chunk 2", "text": "Text 2"},
            ],
            "current_chunk_index": 2,
            "stage1_results": [],
            "presentation_style": "academic",
        }

        result = await node_stage1_process(state)

        assert result["status"] == TaskStatus.MERGING.value
        assert result["stage1_completed"] == 2
        assert result["progress_percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_stage1_process_single_chunk(self):
        """Test processing a single chunk successfully."""
        # Mock the LLMClient initialization and call
        with patch('app.graph.nodes.stage1_processing.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.acomplete.return_value = {
                "content": "# Test Outline",
                "usage": {"total_tokens": 100},
                "model": "deepseek-chat",
                "finish_reason": "stop"
            }
            mock_client_class.return_value = mock_client

            # Also mock the prompt manager
            with patch('app.graph.nodes.stage1_processing.get_prompt_manager') as mock_prompt_mgr:
                mock_prompt_mgr.return_value.format_stage1_prompt.return_value = "Mocked prompt"

                state = {
                    "chunks": [
                        {"id": 1, "title": "Test Chunk", "text": "Test content"},
                    ],
                    "current_chunk_index": 0,
                    "stage1_results": [],
                    "presentation_style": "academic",
                    "execution_log": [],
                }

                result = await node_stage1_process(state)

                assert result["current_chunk_index"] == 1
                assert result["stage1_completed"] == 1
                assert len(result["stage1_results"]) == 1
                assert result["stage1_results"][0]["chunk_id"] == 1
                assert result["stage1_results"][0]["success"] is True
                assert result["stage1_results"][0]["outline"] == "# Test Outline"

                # Verify the LLM was called
                mock_client.acomplete.assert_called_once()

    @pytest.mark.asyncio
    async def test_stage1_process_chunk_failure(self):
        """Test handling chunk processing failure."""
        # Mock both LLMClient and prompt manager
        with patch('app.graph.nodes.stage1_processing.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.acomplete.side_effect = RuntimeError("API Error")
            mock_client_class.return_value = mock_client

            with patch('app.graph.nodes.stage1_processing.get_prompt_manager') as mock_prompt_mgr:
                mock_prompt_mgr.return_value.format_stage1_prompt.return_value = "Mocked prompt"

                state = {
                    "chunks": [
                        {"id": 1, "title": "Test Chunk", "text": "Test content"},
                    ],
                    "current_chunk_index": 0,
                    "stage1_results": [],
                    "presentation_style": "academic",
                    "execution_log": [],
                }

                result = await node_stage1_process(state)

                assert result["current_chunk_index"] == 1
                assert result["stage1_completed"] == 1
                assert len(result["stage1_results"]) == 1
                assert result["stage1_results"][0]["success"] is False
                assert "API Error" in result["stage1_results"][0]["error"]
                assert 1 in result["stage1_failed"]

                # Verify the LLM was called
                mock_client.acomplete.assert_called_once()

    def test_should_continue_stage1_continue(self):
        """Test should_continue_stage1 returns continue."""
        state = {
            "chunks": [
                {"id": 1, "title": "Chunk 1", "text": "Text 1"},
                {"id": 2, "title": "Chunk 2", "text": "Text 2"},
            ],
            "current_chunk_index": 1,
        }

        result = should_continue_stage1(state)
        assert result == "continue"

    def test_should_continue_stage1_merge(self):
        """Test should_continue_stage1 returns merge."""
        state = {
            "chunks": [
                {"id": 1, "title": "Chunk 1", "text": "Text 1"},
            ],
            "current_chunk_index": 1,
        }

        result = should_continue_stage1(state)
        assert result == "merge"


class TestStage2Processing:
    """Test Stage 2 processing node."""

    @pytest.mark.asyncio
    async def test_stage2_process_success(self):
        """Test successful Stage 2 processing."""
        with patch('app.services.llm.provider.LLMClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.acomplete.return_value = {
                "content": "# Marp Markdown",
                "usage": {"total_tokens": 200},
                "model": "deepseek-chat",
                "finish_reason": "stop"
            }
            mock_client_class.return_value = mock_client

            state = {
                "merged_outline": "# Test Outline",
                "presentation_style": "academic",
                "task_id": "test123",
                "execution_log": [],
            }

            result = await node_stage2_process(state)

            assert result["status"] == TaskStatus.RENDERING.value
            assert "marp_markdown" in result
            assert "marp_markdown_path" in result
            assert result["progress_percentage"] == 80.0
            assert len(result["execution_log"]) == 1
            assert result["execution_log"][0]["event"] == "stage2_processed"

    @pytest.mark.asyncio
    async def test_stage2_process_no_outline(self):
        """Test Stage 2 with no merged outline."""
        state = {
            "merged_outline": "",
            "presentation_style": "academic",
            "task_id": "test123",
        }

        result = await node_stage2_process(state)

        assert result["status"] == TaskStatus.FAILED.value
        assert "No merged outline" in result["error_message"]


class TestOutlineMerging:
    """Test outline merging node."""

    def test_merge_outlines_success(self):
        """Test successful outline merging."""
        # Mock the merge function and also mock file operations
        with patch('app.graph.nodes.outline_merging.merge_outlines') as mock_merge, \
             patch('pathlib.Path.write_text') as mock_write, \
             patch('pathlib.Path.mkdir') as mock_mkdir:

            mock_merge.return_value = "# Merged Outline"
            mock_mkdir.return_value = None
            # write_text should not raise an exception, just return None
            mock_write.return_value = None

            state = {
                "stage1_results": [
                    {"chunk_id": 1, "chunk_title": "Chunk 1", "outline": "# Outline 1", "success": True},
                    {"chunk_id": 2, "chunk_title": "Chunk 2", "outline": "# Outline 2", "success": True},
                ],
                "task_id": "test123",
                "execution_log": [],
                "needs_human_review": False,
            }

            # IMPORTANT: node_merge_outlines is SYNC, don't use await!
            result = node_merge_outlines(state)

            assert result["status"] == TaskStatus.STAGE2_PROCESSING.value
            assert result["merged_outline"] == "# Merged Outline"
            assert result["progress_percentage"] == 60.0
            assert result["approved"] is True

            # Verify merge_outlines was called
            mock_merge.assert_called_once()

    def test_merge_outlines_no_results(self):
        """Test merging with no Stage 1 results."""
        state = {
            "stage1_results": [],
            "task_id": "test123",
        }

        # node_merge_outlines is SYNC
        result = node_merge_outlines(state)

        assert result["status"] == TaskStatus.FAILED.value
        assert "No Stage 1 results" in result["error_message"]

    def test_merge_outlines_all_failed(self):
        """Test merging when all Stage 1 results failed."""
        state = {
            "stage1_results": [
                {"chunk_id": 1, "chunk_title": "Chunk 1", "outline": "", "success": False},
                {"chunk_id": 2, "chunk_title": "Chunk 2", "outline": "", "success": False},
            ],
            "task_id": "test123",
        }

        # node_merge_outlines is SYNC
        result = node_merge_outlines(state)

        assert result["status"] == TaskStatus.FAILED.value
        assert "All Stage 1 processing failed" in result["error_message"]


class TestPDFParsing:
    """Test PDF parsing node."""

    def test_parse_pdf_file_not_found(self):
        """Test PDF parsing with missing file."""
        state = {
            "pdf_path": Path("nonexistent.pdf"),
            "task_id": "test123",
        }

        # node_parse_pdf is SYNC
        result = node_parse_pdf(state)

        assert result["status"] == TaskStatus.FAILED.value
        assert "not found" in result["error_message"].lower()


class TestRendering:
    """Test rendering node."""

    def test_render_success(self):
        """Test successful rendering."""
        with patch('app.services.renderer.marp_engine.MarpEngine') as mock_engine_class:
            mock_engine = MagicMock()
            mock_engine.render.return_value = True
            mock_engine_class.return_value = mock_engine

            # Create temporary markdown file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write("# Test")
                md_path = Path(f.name)

            try:
                state = {
                    "marp_markdown": "# Test Markdown",
                    "marp_markdown_path": str(md_path),
                    "output_format": "pptx",
                    "task_id": "test123",
                    "execution_log": [],
                }

                # node_render is SYNC
                result = node_render(state)

                assert result["status"] == TaskStatus.COMPLETED.value
                assert "output_path" in result
                assert result["progress_percentage"] == 100.0
                assert len(result["execution_log"]) == 1
                assert result["execution_log"][0]["event"] == "rendering_complete"
            finally:
                # Cleanup
                md_path.unlink()

    def test_render_no_markdown(self):
        """Test rendering with no markdown."""
        state = {
            "marp_markdown": "",
            "marp_markdown_path": "",
            "output_format": "pptx",
            "task_id": "test123",
        }

        # node_render is SYNC
        result = node_render(state)

        assert result["status"] == TaskStatus.FAILED.value
        assert "No Marp Markdown" in result["error_message"]


if __name__ == "__main__":
    pytest.main([__file__])
