"""Test suite for prompt template system."""
import json
import tempfile
import shutil
from pathlib import Path

import pytest

from app.services.llm.prompts.prompt_templates import (
    PromptTemplateManager,
    save_custom_templates,
    get_available_styles,
    format_stage1_prompt,
    format_stage2_prompt,
    PROMPT_STORAGE_DIR,
)


class TestPromptTemplates:
    """Test cases for prompt template system."""

    def test_templates_json_exists_and_valid(self):
        """Test that templates.json exists and contains valid JSON."""
        templates_file = Path("app/services/llm/prompts/templates.json")

        assert templates_file.exists(), "templates.json should exist"

        with open(templates_file, 'r', encoding='utf-8') as f:
            templates = json.load(f)

        assert 'stage1' in templates, "templates.json should have stage1"
        assert 'stage2' in templates, "templates.json should have stage2"

        required_styles = ['academic', 'popular', 'business']
        for style in required_styles:
            assert style in templates['stage1'], f"Missing stage1 template for {style}"
            assert style in templates['stage2'], f"Missing stage2 template for {style}"

    def test_prompt_manager_initialization(self):
        """Test PromptTemplateManager initialization."""
        manager = PromptTemplateManager()

        assert manager._preset_templates is not None
        assert 'stage1' in manager._preset_templates
        assert 'stage2' in manager._preset_templates

    def test_get_available_styles(self):
        """Test getting available preset styles."""
        styles = get_available_styles()

        assert isinstance(styles, list)
        assert len(styles) > 0
        assert 'academic' in styles

    def test_get_preset_template(self):
        """Test getting preset templates."""
        manager = PromptTemplateManager()

        # Test Stage 1 academic template
        template = manager.get_template(
            task_id=None,
            stage="stage1",
            style="academic"
        )
        assert template is not None
        assert len(template) > 100
        assert "{content}" in template

        # Test Stage 2 academic template
        template = manager.get_template(
            task_id=None,
            stage="stage2",
            style="academic"
        )
        assert template is not None
        assert len(template) > 100
        assert "{outline}" in template

    def test_format_stage1_prompt(self):
        """Test Stage 1 prompt formatting."""
        prompt = format_stage1_prompt(
            style="academic",
            content="Test content",
            task_id=None
        )

        assert "{content}" not in prompt
        assert "Test content" in prompt
        assert len(prompt) > 100

    def test_format_stage2_prompt(self):
        """Test Stage 2 prompt formatting."""
        prompt = format_stage2_prompt(
            style="academic",
            outline="Test outline",
            task_id=None
        )

        assert "{outline}" not in prompt
        assert "Test outline" in prompt
        assert len(prompt) > 100

    def test_custom_templates_save_and_load(self):
        """Test saving and loading custom templates."""
        # Create temporary directory for testing
        test_dir = Path(tempfile.mkdtemp())
        test_task_id = "test123"

        try:
            # Override PROMPT_STORAGE_DIR temporarily
            import app.services.llm.prompts.prompt_templates as pt_module
            original_dir = pt_module.PROMPT_STORAGE_DIR
            pt_module.PROMPT_STORAGE_DIR = test_dir

            # Save custom templates
            save_custom_templates(
                task_id=test_task_id,
                stage1_template="Custom Stage 1: {content}",
                stage2_template="Custom Stage 2: {outline}",
            )

            # Verify file was created
            prompt_file = test_dir / test_task_id / "prompt.json"
            assert prompt_file.exists(), "Prompt file should be created"

            # Load and verify custom templates
            manager = PromptTemplateManager()
            template = manager.get_template(
                task_id=test_task_id,
                stage="stage1",
                style="academic"
            )
            assert "Custom Stage 1" in template

            template = manager.get_template(
                task_id=test_task_id,
                stage="stage2",
                style="academic"
            )
            assert "Custom Stage 2" in template

            # Restore original directory
            pt_module.PROMPT_STORAGE_DIR = original_dir

        finally:
            # Cleanup
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_custom_template_overrides_preset(self):
        """Test that custom templates override preset templates."""
        test_dir = Path(tempfile.mkdtemp())
        test_task_id = "test_override"

        try:
            import app.services.llm.prompts.prompt_templates as pt_module
            original_dir = pt_module.PROMPT_STORAGE_DIR
            pt_module.PROMPT_STORAGE_DIR = test_dir

            # Save custom template
            save_custom_templates(
                task_id=test_task_id,
                stage1_template="CUSTOM TEMPLATE",
                stage2_template=None,  # Don't override stage2
            )

            # Get template for the task
            manager = PromptTemplateManager()

            # Should get custom template for stage1
            template = manager.get_template(
                task_id=test_task_id,
                stage="stage1",
                style="academic"
            )
            assert "CUSTOM TEMPLATE" in template

            # Should get preset template for stage2 (not overridden)
            template = manager.get_template(
                task_id=test_task_id,
                stage="stage2",
                style="academic"
            )
            assert "CUSTOM TEMPLATE" not in template
            assert len(template) > 100

            pt_module.PROMPT_STORAGE_DIR = original_dir

        finally:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_style_parameter_capitalization(self):
        """Test that {style} placeholder is replaced correctly."""
        prompt = format_stage1_prompt(
            style="academic",
            content="Test",
            task_id=None
        )

        # Should capitalize the style name
        assert "{style}" not in prompt
        # The actual replacement depends on the template

    def test_empty_task_id_uses_preset(self):
        """Test that None task_id uses preset templates."""
        manager = PromptTemplateManager()

        template_with_id = manager.get_template(
            task_id="nonexistent",
            stage="stage1",
            style="academic"
        )

        template_without_id = manager.get_template(
            task_id=None,
            stage="stage1",
            style="academic"
        )

        # Both should return the same preset template
        assert template_with_id == template_without_id
