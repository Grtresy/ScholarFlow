"""Prompt Manager for loading and formatting prompt templates."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional


class PromptManager:
    """Manages prompt templates from Prompt模板清单.md"""

    def __init__(self, prompt_file: Optional[Path] = None):
        """Initialize prompt manager.

        Args:
            prompt_file: Path to the prompt template file. If None, uses default.
        """
        if prompt_file is None:
            prompt_file = Path(__file__).parent / "llm" / "prompts" / "Prompt模板清单.md"

        self.prompt_file = prompt_file
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load all prompts from the markdown file.

        Returns:
            Dict containing all prompts organized by stage and style.
        """
        content = self.prompt_file.read_text(encoding="utf-8")

        prompts = {
            "stage1": {
                "academic": "",
                "popular": "",
                "business": ""
            },
            "stage2": {
                "academic": "",
                "popular": "",
                "business": ""
            }
        }

        # Extract Stage 1 Academic
        stage1_academic_match = re.search(
            r'## 1\.1 学术汇报风（Stage 1）.*?【角色设定结束】(.*?)【任务与输入】.*?【MinerU 输出结束】',
            content,
            re.DOTALL
        )
        if stage1_academic_match:
            prompts["stage1"]["academic"] = stage1_academic_match.group(0).strip()

        # Extract Stage 1 Popular Science
        stage1_popular_match = re.search(
            r'## 1\.2 科普简介风（Stage 1）.*?【角色设定结束】(.*?)【任务与输入】.*?【MinerU 输出结束】',
            content,
            re.DOTALL
        )
        if stage1_popular_match:
            prompts["stage1"]["popular"] = stage1_popular_match.group(0).strip()

        # Extract Stage 1 Business
        stage1_business_match = re.search(
            r'## 1\.3 商业路演风（Stage 1）.*?【角色设定结束】(.*?)【任务与输入】.*?【MinerU 输出结束】',
            content,
            re.DOTALL
        )
        if stage1_business_match:
            prompts["stage1"]["business"] = stage1_business_match.group(0).strip()

        # Extract Stage 2 Academic
        stage2_academic_match = re.search(
            r'## 2\.1 学术汇报风（Stage 2）.*?【角色设定结束】(.*?)【任务与输入】.*?【大纲】',
            content,
            re.DOTALL
        )
        if stage2_academic_match:
            prompts["stage2"]["academic"] = stage2_academic_match.group(0).strip()

        # Extract Stage 2 Popular Science
        stage2_popular_match = re.search(
            r'## 2\.2 科普简介风（Stage 2）.*?【角色设定结束】(.*?)【任务与输入】.*?【大纲】',
            content,
            re.DOTALL
        )
        if stage2_popular_match:
            prompts["stage2"]["popular"] = stage2_popular_match.group(0).strip()

        # Extract Stage 2 Business
        stage2_business_match = re.search(
            r'## 2\.3 商业路演风（Stage 2）.*?【角色设定结束】(.*?)【任务与输入】.*?【大纲】',
            content,
            re.DOTALL
        )
        if stage2_business_match:
            prompts["stage2"]["business"] = stage2_business_match.group(0).strip()

        return prompts

    def get_stage1_prompt(self, style: str = "academic") -> str:
        """Get Stage 1 prompt for a specific style.

        Args:
            style: One of 'academic', 'popular', or 'business'

        Returns:
            The formatted Stage 1 prompt
        """
        style_key = style.lower()
        if style_key not in self.prompts["stage1"]:
            raise ValueError(f"Unknown style: {style}. Use 'academic', 'popular', or 'business'")

        return self.prompts["stage1"][style_key]

    def get_stage2_prompt(self, style: str = "academic") -> str:
        """Get Stage 2 prompt for a specific style.

        Args:
            style: One of 'academic', 'popular', or 'business'

        Returns:
            The formatted Stage 2 prompt
        """
        style_key = style.lower()
        if style_key not in self.prompts["stage2"]:
            raise ValueError(f"Unknown style: {style}. Use 'academic', 'popular', or 'business'")

        return self.prompts["stage2"][style_key]

    def format_stage1_prompt(self, style: str, chunk_text: str) -> str:
        """Format Stage 1 prompt with chunk text.

        Args:
            style: Presentation style ('academic', 'popular', 'business')
            chunk_text: The markdown chunk text from MinerU

        Returns:
            Complete prompt ready for LLM
        """
        base_prompt = self.get_stage1_prompt(style)
        return f"{base_prompt}\n\n【MinerU 输出开始】\n\n{chunk_text}\n\n【MinerU 输出结束】"

    def format_stage2_prompt(self, style: str, outline: str) -> str:
        """Format Stage 2 prompt with merged outline.

        Args:
            style: Presentation style ('academic', 'popular', 'business')
            outline: The merged outline from Stage 1

        Returns:
            Complete prompt ready for LLM
        """
        base_prompt = self.get_stage2_prompt(style)
        return f"{base_prompt}\n\n【大纲】\n\n{outline}"


# Global instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
