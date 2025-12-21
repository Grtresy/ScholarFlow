"""Prompt templates for Stage 1/2 generation with dynamic loading support."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
TEMPLATES_FILE = ROOT / "templates.json"
RAW_MARKDOWN = ROOT / "Prompt 模板清单.md"

# Task-specific prompt storage
PROMPT_STORAGE_DIR = Path("data/workflow/intermediate")


class PromptTemplateManager:
    """Manages prompt templates with support for preset and custom templates."""

    def __init__(self):
        self._load_preset_templates()

    def _load_preset_templates(self):
        """Load preset templates from JSON file."""
        self._preset_templates = {}
        try:
            if TEMPLATES_FILE.exists():
                with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                    self._preset_templates = json.load(f)
                logger.info(f"Loaded preset templates from {TEMPLATES_FILE}")
            else:
                logger.warning(f"Templates file not found: {TEMPLATES_FILE}")
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            self._preset_templates = {}

    def _get_prompt_file(self, task_id: str) -> Path:
        """Get the path to the prompt JSON file for a task."""
        task_dir = PROMPT_STORAGE_DIR / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir / "prompt.json"

    def save_custom_templates(self, task_id: str, stage1_template: Optional[str] = None,
                            stage2_template: Optional[str] = None):
        """
        Save custom templates for a task to JSON file.

        Args:
            task_id: Task identifier
            stage1_template: Custom Stage 1 template (optional)
            stage2_template: Custom Stage 2 template (optional)
        """
        prompt_file = self._get_prompt_file(task_id)

        # Load existing or create new
        if prompt_file.exists():
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read existing prompt file: {e}")
                data = {}
        else:
            data = {}

        # Update with new templates
        if stage1_template is not None:
            data['stage1'] = stage1_template
        if stage2_template is not None:
            data['stage2'] = stage2_template

        # Save to file
        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved custom templates for task {task_id} to {prompt_file}")
        except Exception as e:
            logger.error(f"Failed to save prompt file: {e}")
            raise

    def load_custom_templates(self, task_id: str) -> Dict[str, Optional[str]]:
        """
        Load custom templates for a task from JSON file.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with 'stage1' and 'stage2' keys (values may be None)
        """
        prompt_file = self._get_prompt_file(task_id)

        if not prompt_file.exists():
            logger.info(f"No custom templates found for task {task_id}")
            return {'stage1': None, 'stage2': None}

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                'stage1': data.get('stage1'),
                'stage2': data.get('stage2')
            }
        except Exception as e:
            logger.error(f"Failed to load prompt file for task {task_id}: {e}")
            return {'stage1': None, 'stage2': None}

    def get_template(self, task_id: Optional[str], stage: str, style: str = "academic") -> str:
        """
        Get template for a specific task, stage, and style.

        Priority:
        1. Custom template for task_id (from prompt.json)
        2. Preset template from JSON
        3. Embedded fallback template

        Args:
            task_id: Task identifier (None for global lookup)
            stage: 'stage1' or 'stage2'
            style: Style name (academic, popular, business)

        Returns:
            Template string
        """
        # Check custom template first
        custom_templates = {}
        if task_id:
            custom_templates = self.load_custom_templates(task_id)
            if custom_templates.get(stage):
                logger.info(f"Using custom {stage} template for task {task_id}")
                return custom_templates[stage]

        # Check preset templates
        if stage in self._preset_templates and style in self._preset_templates[stage]:
            return self._preset_templates[stage][style]

        # Fallback to embedded templates
        embedded = _EMBEDDED_TEMPLATES.get(stage, {})
        fallback = embedded.get(style, embedded.get("academic", ""))
        if fallback:
            logger.warning(f"Using embedded fallback for {stage}, style={style}")

        return fallback

    def format_prompt(self, task_id: Optional[str], stage: str, style: str, **kwargs) -> str:
        """
        Format a prompt template with provided variables.

        Args:
            task_id: Task identifier
            stage: 'stage1' or 'stage2'
            style: Style name
            **kwargs: Variables to replace in template (e.g., content, outline)

        Returns:
            Formatted prompt string
        """
        template = self.get_template(task_id, stage, style)

        # Replace all {variable} placeholders with provided values
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            template = template.replace(placeholder, str(value))

        # Handle {style} placeholder specially (capitalize for backward compatibility)
        if "{style}" in template:
            template = template.replace("{style}", style.capitalize())

        return template

    def get_available_styles(self) -> list[str]:
        """Get list of available preset styles."""
        styles = set()

        if "stage1" in self._preset_templates:
            styles.update(self._preset_templates["stage1"].keys())
        if "stage2" in self._preset_templates:
            styles.update(self._preset_templates["stage2"].keys())

        return sorted(list(styles))


def load_raw_markdown() -> str:
    """Load the raw markdown documentation file."""
    return RAW_MARKDOWN.read_text(encoding="utf-8")


# Global instance
_template_manager = PromptTemplateManager()


# Convenience functions
def get_stage1_template(style: str = "academic", task_id: Optional[str] = None) -> str:
    """Get Stage 1 template."""
    return _template_manager.get_template(task_id, "stage1", style)


def get_stage2_template(style: str = "academic", task_id: Optional[str] = None) -> str:
    """Get Stage 2 template."""
    return _template_manager.get_template(task_id, "stage2", style)


def format_stage1_prompt(style: str, content: str, task_id: Optional[str] = None, user_modifications: str = "") -> str:
    """Format Stage 1 prompt with content and optional user modifications."""
    return _template_manager.format_prompt(task_id, "stage1", style, content=content, user_modifications=user_modifications)


def format_stage2_prompt(style: str, outline: str, task_id: Optional[str] = None, user_modifications: str = "") -> str:
    """Format Stage 2 prompt with outline and optional user modifications."""
    return _template_manager.format_prompt(task_id, "stage2", style, outline=outline, user_modifications=user_modifications)


def save_custom_templates(task_id: str, stage1_template: Optional[str] = None,
                        stage2_template: Optional[str] = None):
    """Save custom templates for a task."""
    _template_manager.save_custom_templates(task_id, stage1_template, stage2_template)


def get_available_styles() -> list[str]:
    """Get list of available preset styles."""
    return _template_manager.get_available_styles()


# # Embedded fallback templates
# _EMBEDDED_TEMPLATES = {
#     "stage1": {
#         "academic": """你现在是一个"学术会议汇报 PPT 大纲生成助手（Stage 1）"。

# **输入**：一份由 MinerU 导出的论文 Markdown 文本片段。

# **目标**：基于当前这份 MinerU 文本片段，生成一份适合学术汇报风格的 PPT 草案大纲。

# 【MinerU 输出开始】
# {content}
# 【MinerU 输出结束】

# 请开始生成大纲：""",

#         "popular": """你现在是一个"面向非专业听众的科普 PPT 大纲生成助手（Stage 1）"。

# **输入**：一份由 MinerU 导出的论文 Markdown 文本片段。

# **目标**：基于当前这份文本片段，生成一份"科普简介风"的 PPT 草案大纲。

# 【MinerU 输出开始】
# {content}
# 【MinerU 输出结束】

# 请开始生成大纲：""",

#         "business": """你现在是一个"商业路演风 PPT 大纲生成助手（Stage 1）"。

# **输入**：一份由 MinerU 导出的论文 Markdown 文本片段。

# **目标**：基于当前这部分技术论文内容，生成一份商业路演风 PPT 大纲片段。

# 【MinerU 输出开始】
# {content}
# 【MinerU 输出结束】

# 请开始生成大纲："""
#     },
#     "stage2": {
#         "academic": """你现在是一个"学术汇报风 Marp 格式 PPT 文稿生成助手（Stage 2）"。

# **输入**：一份已经由人类或 Stage 1 整体拼接并确认过的 PPT 大纲。

# **目标**：根据这份大纲，生成一份可以直接用 Marp 渲染的 Markdown 文稿，风格为学术汇报风。

# 【大纲】
# {outline}

# 请开始生成 Marp Markdown：""",

#         "popular": """你现在是一个"面向非专业听众的科普 PPT 文稿生成助手（Stage 2）"。

# **输入**：一份已经由人类或 Stage 1 整体拼接并确认过的 PPT 大纲。

# **目标**：将这份大纲转换成一份可以直接用 Marp 渲染的 Markdown 文稿，风格为"科普简介风"。

# 【大纲】
# {outline}

# 请开始生成 Marp Markdown：""",

#         "business": """你现在是一个"面向投资人 / 业务决策者的商业路演 PPT 文稿生成助手（Stage 2）"。

# **输入**：一份已经由人类或 Stage 1 整体拼接并确认过的 PPT 大纲。

# **目标**：将这份大纲转换成一份可以直接用 Marp 渲染的 Markdown 文稿，风格为"商业路演风"。

# 【大纲】
# {outline}

# 请开始生成 Marp Markdown："""
#     }
# }

# # Backward compatibility
# STAGE1_PROMPT = _EMBEDDED_TEMPLATES["stage1"]["academic"]
# STAGE2_PROMPT = _EMBEDDED_TEMPLATES["stage2"]["academic"]
