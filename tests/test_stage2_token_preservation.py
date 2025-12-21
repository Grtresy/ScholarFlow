"""Test Stage 2 token preservation for all presentation styles.

This test ensures that all three presentation styles (academic, popular, business)
correctly preserve image tokens [[TOKEN_IMG_XXX]] throughout the Stage 2 processing.
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from app.graph.state import WorkflowState, PresentationStyle, TaskStatus
from app.graph.nodes.stage2_processing import node_stage2_process
from app.services.llm.provider import LLMClient


class TestStage2TokenPreservation:
    """Test that Stage 2 preserves tokens correctly for all styles."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_state(self, temp_dir):
        """Create a sample workflow state with tokenized content."""
        task_id = "test_task_123"
        state: WorkflowState = {
            "task_id": task_id,
            "presentation_style": "academic",
            "merged_outline": """Slide 1：标题
- 要点1
- 图：学习率范围测试的训练与验证曲线 [[TOKEN_IMG_001]]

Slide 2：标题
- 要点1
- 要点2
- 图：对比新旧训练方式在速度和效果上的差异 [[TOKEN_IMG_002]]
""",
            "image_token_map": {
                "[[TOKEN_IMG_001]]": {
                    "hash": "df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0",
                    "alt_text": "Figure 1: CIFAR-10 results",
                    "original_path": "images/df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg",
                    "filename": "df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg"
                },
                "[[TOKEN_IMG_002]]": {
                    "hash": "2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65",
                    "alt_text": "Figure 2: Training comparison",
                    "original_path": "images/2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65.jpg",
                    "filename": "2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65.jpg"
                }
            },
            "token_count": 2,
            "execution_log": [],
        }
        return state

    @pytest.mark.asyncio
    async def test_academic_style_preserves_tokens(self, sample_state):
        """Test that academic style preserves tokens correctly."""
        sample_state["presentation_style"] = "academic"

        result = await node_stage2_process(sample_state)

        assert result["status"] == TaskStatus.RENDERING.value
        assert "marp_markdown" in result

        marp_markdown = result["marp_markdown"]

        # Verify that tokens are preserved
        assert "[[TOKEN_IMG_001]]" in marp_markdown
        assert "[[TOKEN_IMG_002]]" in marp_markdown

        # Verify that tokens are NOT converted to image paths
        assert "images/df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg" not in marp_markdown
        assert "images/2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65.jpg" not in marp_markdown

        # Verify that tokens are NOT converted to generic paths like images/xxx.jpg
        assert "images/xxx.jpg" not in marp_markdown

        # Verify that token count is preserved
        assert result["token_count"] == 2
        assert result["image_token_map"] == sample_state["image_token_map"]

    @pytest.mark.asyncio
    async def test_popular_style_preserves_tokens(self, sample_state):
        """Test that popular style preserves tokens correctly (after fix)."""
        sample_state["presentation_style"] = "popular"

        result = await node_stage2_process(sample_state)

        assert result["status"] == TaskStatus.RENDERING.value
        assert "marp_markdown" in result

        marp_markdown = result["marp_markdown"]

        # Verify that tokens are preserved (this is the fix)
        assert "[[TOKEN_IMG_001]]" in marp_markdown
        assert "[[TOKEN_IMG_002]]" in marp_markdown

        # Verify that tokens are NOT converted to image paths
        assert "images/df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg" not in marp_markdown
        assert "images/2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65.jpg" not in marp_markdown

        # Verify that tokens are NOT converted to generic paths like images/xxx.jpg
        assert "images/xxx.jpg" not in marp_markdown

        # Verify that token count is preserved
        assert result["token_count"] == 2
        assert result["image_token_map"] == sample_state["image_token_map"]

    @pytest.mark.asyncio
    async def test_business_style_preserves_tokens(self, sample_state):
        """Test that business style preserves tokens correctly (after fix)."""
        sample_state["presentation_style"] = "business"

        result = await node_stage2_process(sample_state)

        assert result["status"] == TaskStatus.RENDERING.value
        assert "marp_markdown" in result

        marp_markdown = result["marp_markdown"]

        # Verify that tokens are preserved (this is the fix)
        assert "[[TOKEN_IMG_001]]" in marp_markdown
        assert "[[TOKEN_IMG_002]]" in marp_markdown

        # Verify that tokens are NOT converted to image paths
        assert "images/df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg" not in marp_markdown
        assert "images/2e91889abe47de1d8c146c7997719d4a4ed0ce07d4080a6ecaee8ed56ae5af65.jpg" not in marp_markdown

        # Verify that tokens are NOT converted to generic paths like images/xxx.jpg
        assert "images/xxx.jpg" not in marp_markdown

        # Verify that token count is preserved
        assert result["token_count"] == 2
        assert result["image_token_map"] == sample_state["image_token_map"]

    @pytest.mark.asyncio
    async def test_all_styles_generate_correct_token_map(self, sample_state):
        """Test that all three styles correctly pass through the token map."""
        styles = ["academic", "popular", "business"]

        for style in styles:
            sample_state["presentation_style"] = style
            result = await node_stage2_process(sample_state)

            # Verify token map is preserved
            assert result["image_token_map"] == sample_state["image_token_map"], \
                f"Token map not preserved for style: {style}"

            # Verify token count is correct
            assert result["token_count"] == 2, \
                f"Token count incorrect for style: {style}"

            # Verify markdown was generated
            assert "marp_markdown" in result, \
                f"No markdown generated for style: {style}"
            assert len(result["marp_markdown"]) > 0, \
                f"Empty markdown for style: {style}"

    @pytest.mark.asyncio
    async def test_system_prompt_is_loaded(self):
        """Test that the global system prompt can be loaded."""
        from app.services.llm.provider import load_global_system_prompt

        system_prompt = load_global_system_prompt("token_protection")

        # Verify that system prompt exists and contains token protection rules
        assert system_prompt is not None
        assert "TOKEN_IMG_XXX" in system_prompt
        assert "不能修改" in system_prompt or "不能更改" in system_prompt

    @pytest.mark.asyncio
    async def test_llm_client_uses_system_prompt(self):
        """Test that LLMClient automatically uses system prompt."""
        # This test verifies that the LLMClient is configured to use
        # the token protection system prompt by default

        # We can't easily test this without mocking the actual API call,
        # but we can verify the method signature accepts system_prompt
        client = LLMClient()

        # Verify the method has system_prompt parameter
        import inspect
        sig = inspect.signature(client.acomplete)
        assert "system_prompt" in sig.parameters

    def test_stage2_template_consistency(self):
        """Test that all Stage 2 templates have consistent token handling rules."""
        from app.services.llm.prompts.prompt_templates import PromptTemplateManager

        manager = PromptTemplateManager()
        templates = manager._preset_templates.get("stage2", {})

        # Check that all three styles have token handling rules
        for style in ["academic", "popular", "business"]:
            assert style in templates, f"Missing {style} template"

            template = templates[style]

            # Verify template mentions token preservation
            assert "Token" in template or "token" in template, \
                f"{style} template doesn't mention tokens"

            # Verify template doesn't instruct to remove tokens (this was the bug)
            # The old popular and business templates had "绝对不要保留 [[TOKEN_IMG_XXX]] 标记"
            # The fixed templates should NOT have this instruction
            bad_instruction = "绝对不要保留 `[[TOKEN_IMG_XXX]]` 标记"
            assert bad_instruction not in template, \
                f"{style} template still contains old buggy instruction to remove tokens"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
