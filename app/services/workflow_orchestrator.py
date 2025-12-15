"""Workflow Orchestrator for coordinating the complete pipeline."""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import get_settings
from app.services.llm_logger import LLMCallLogger
from app.services.llm.provider import call_model
from app.services.parser.image_manager import create_image_manager, ValidationResult
from app.services.prompt_manager import get_prompt_manager
from app.services.llm.merge import main as merge_main
from app.services.llm.split import main as split_main


class WorkflowOrchestrator:
    """Orchestrates the complete workflow: split → stage1 loop → merge → stage2 → render"""

    def __init__(self, data_dir: str, logger: LLMCallLogger):
        """Initialize the workflow orchestrator.

        Args:
            data_dir: Base data directory
            logger: LLM call logger instance
        """
        self.data_dir = Path(data_dir)
        self.logger = logger
        self.settings = get_settings()
        self.prompt_manager = get_prompt_manager()
        self.image_manager = create_image_manager(data_dir)

    async def execute_full_workflow(
        self,
        pdf_path: str,
        presentation_style: str = "academic",
        max_chars: int = 6000,
        target_chunks: int = 6
    ) -> Dict[str, Any]:
        """Execute the complete workflow.

        Args:
            pdf_path: Path to the input PDF file
            presentation_style: One of 'academic', 'popular', 'business'
            max_chars: Maximum characters per chunk
            target_chunks: Target number of chunks

        Returns:
            Dict containing workflow results
        """
        self.logger.log_summary(f"开始处理 PDF: {Path(pdf_path).name}")
        self.logger.log_summary(f"演示风格: {presentation_style}")
        self.logger.log_summary(f"最大分块大小: {max_chars} 字符")
        self.logger.log_summary(f"目标分块数: {target_chunks}")

        start_time = datetime.now()

        # Step 1: Parse PDF with MinerU
        markdown_text = await self._parse_with_mineru(pdf_path)
        markdown_path = self.data_dir / "intermediates" / self.logger.task_id / "markdown"
        markdown_path.mkdir(parents=True, exist_ok=True)
        (markdown_path / "paper.md").write_text(markdown_text, encoding="utf-8")

        # Step 2: Split markdown into chunks
        self.logger.log_summary("\n📄 [Step 1/4] Splitting markdown into chunks...")
        split_result = self._split_markdown(
            markdown_text,
            max_chars=max_chars,
            target_chunks=target_chunks
        )
        chunks = split_result["chunks"]
        self.logger.log_summary(f"分块完成: {len(chunks)} 个 chunks")

        # Save chunks for debugging
        chunks_file = self.data_dir / "intermediates" / self.logger.task_id / "chunks.json"
        import json
        chunks_file.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

        # Step 3: Process each chunk with Stage 1 LLM
        self.logger.log_summary(f"\n📝 [Step 2/4] Processing {len(chunks)} chunks with Stage 1 LLM...")
        stage1_results = []
        for i, chunk in enumerate(chunks, 1):
            self.logger.log_summary(f"  └─ 处理 chunk {i}/{len(chunks)}: {chunk.get('title', 'Untitled')[:50]}")
            outline = await self._process_chunk_stage1(
                chunk,
                presentation_style
            )
            stage1_results.append({
                "chunk_id": chunk["id"],
                "chunk_title": chunk.get("title", f"Chunk {chunk['id']}"),
                "outline": outline
            })

        # Save stage1 results
        stage1_file = self.data_dir / "intermediates" / self.logger.task_id / "stage1_results.json"
        stage1_file.write_text(
            json.dumps(stage1_results, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # Step 4: Merge all Stage 1 outputs
        self.logger.log_summary(f"\n🔄 [Step 3/4] Merging {len(stage1_results)} outlines...")
        merged_outline = self._merge_outlines(stage1_results)
        self.logger.log_summary("大纲合并完成")

        # Save merged outline
        merged_outline_file = self.data_dir / "intermediates" / self.logger.task_id / "merged_outline.md"
        merged_outline_file.write_text(merged_outline, encoding="utf-8")

        # Step 5: Stage 2 LLM
        self.logger.log_summary("\n🎨 [Step 4/4] Generating Marp Markdown with Stage 2 LLM...")
        marp_markdown = await self._process_stage2(
            merged_outline,
            presentation_style
        )

        # Save marp markdown
        marp_file = self.data_dir / "intermediates" / self.logger.task_id / "final_outline.md"
        marp_file.write_text(marp_markdown, encoding="utf-8")

        # Step 6: Render with Marp
        self.logger.log_summary("\n🎨 Rendering presentation with Marp...")
        output_path = await self._render_marp(marp_markdown)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Final summary
        self.logger.log_summary(f"""
✅ Workflow 执行成功！

**任务ID**: {self.logger.task_id}
**耗时**: {duration:.2f} 秒
**演示风格**: {presentation_style}
**处理 chunks**: {len(chunks)} 个
**输出文件**: {output_path}
""")

        return {
            "status": "success",
            "task_id": self.logger.task_id,
            "duration": duration,
            "output_path": output_path,
            "chunks_count": len(chunks),
            "merged_outline": merged_outline,
            "marp_markdown": marp_markdown
        }

    async def _parse_with_mineru(self, pdf_path: str) -> str:
        """Parse PDF with MinerU.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Markdown text extracted from PDF
        """
        # For now, simulate MinerU parsing
        # TODO: Implement actual MinerU integration
        self.logger.log_summary("📄 [MinerU] PDF parsing not yet implemented, using mock data")

        # Return mock markdown for testing
        mock_markdown = """# Cyclical Learning Rates for Training Neural Networks

Leslie N. Smith
U.S. Naval Research Laboratory

## Abstract

We propose a new method for setting the learning rate called cyclical learning rates.

## 1. Introduction

Training deep neural networks is time-consuming. Learning rate is critical.

## 2. Method

We use cyclical learning rates that vary between a lower and upper bound.

## 3. Experiments

Experiments on CIFAR-10 and ImageNet show improved performance.

## 4. Conclusion

Our method is simple and effective for training neural networks.
"""
        return mock_markdown

    def _split_markdown(
        self,
        markdown_text: str,
        max_chars: int,
        target_chunks: int
    ) -> Dict[str, Any]:
        """Split markdown using the langchain split component.

        Args:
            markdown_text: The markdown text to split
            max_chars: Maximum characters per chunk
            target_chunks: Target number of chunks

        Returns:
            Dict containing the split chunks
        """
        inputs = {
            "markdown": markdown_text,
            "max_chars": max_chars,
            "target_chunks": target_chunks
        }
        return split_main(inputs)

    async def _process_chunk_stage1(
        self,
        chunk: Dict[str, Any],
        presentation_style: str
    ) -> str:
        """Process a single chunk with Stage 1 LLM.

        Args:
            chunk: The chunk to process
            presentation_style: The presentation style

        Returns:
            Generated outline for this chunk
        """
        # Tokenize image references in chunk text
        tokenized_text, extracted_tokens = self.image_manager.tokenize_image_references(
            chunk["text"]
        )

        # Format prompt with tokenized chunk text
        full_prompt = self.prompt_manager.format_stage1_prompt(
            style=presentation_style,
            chunk_text=tokenized_text
        )

        # Call LLM
        response = call_model(
            prompt=full_prompt,
            max_tokens=4000,
            temperature=0.7
        )

        # Log the call
        self.logger.log_call(
            step_name=f"Stage1-{chunk['id']}-{chunk.get('title', 'Untitled')[:30]}",
            prompt=full_prompt,
            model=self.settings.llm_model,
            response=response
        )

        # Validate extracted tokens
        if extracted_tokens:
            task_id = self.logger.task_id
            token_list = [f"[[IMAGE:{token}]]" for token in extracted_tokens]
            validation_result = self.image_manager.validate_image_tokens(
                token_list, task_id
            )

            if validation_result.invalid_tokens:
                # Prompt user for action
                report = self.image_manager.report_validation_issues(
                    validation_result, task_id
                )
                self.logger.log_summary(report)

                # For now, just log and continue (in production, would ask user)
                self.logger.log_summary(
                    f"⚠️  发现 {len(validation_result.invalid_tokens)} 个无效图片标记，但继续处理..."
                )

        return response["content"]

    def _merge_outlines(self, items: List[Dict[str, Any]]) -> str:
        """Merge multiple outlines using the langchain merge component.

        Args:
            items: List of dicts with chunk_id, chunk_title, and outline

        Returns:
            Merged outline text
        """
        inputs = {"items": items}
        result = merge_main(inputs)
        return result["outline_merged"]

    async def _process_stage2(
        self,
        merged_outline: str,
        presentation_style: str
    ) -> str:
        """Process merged outline with Stage 2 LLM.

        Args:
            merged_outline: The merged outline from Stage 1
            presentation_style: The presentation style

        Returns:
            Marp Markdown for rendering
        """
        # Validate merged outline for image tokens before Stage 2
        task_id = self.logger.task_id
        outline_tokens = self._extract_tokens_from_text(merged_outline)

        if outline_tokens:
            validation_result = self.image_manager.validate_image_tokens(
                outline_tokens, task_id
            )

            if validation_result.invalid_tokens:
                # Prompt user for action
                report = self.image_manager.report_validation_issues(
                    validation_result, task_id
                )
                self.logger.log_summary(report)

                # For now, just log and continue (in production, would ask user)
                self.logger.log_summary(
                    f"⚠️  发现 {len(validation_result.invalid_tokens)} 个无效图片标记，但继续处理..."
                )

        # Format prompt with merged outline
        full_prompt = self.prompt_manager.format_stage2_prompt(
            style=presentation_style,
            outline=merged_outline
        )

        # Call LLM
        response = call_model(
            prompt=full_prompt,
            max_tokens=8000,
            temperature=0.7
        )

        # Log the call
        self.logger.log_call(
            step_name=f"Stage2-{presentation_style}",
            prompt=full_prompt,
            model=self.settings.llm_model,
            response=response
        )

        # Restore tokens to proper image URLs in the output
        marp_markdown = self.image_manager.restore_tokens_to_markdown(
            response["content"], task_id
        )

        return marp_markdown

    def _extract_tokens_from_text(self, text: str) -> List[str]:
        """Extract all image tokens from text.

        Args:
            text: Text containing image tokens

        Returns:
            List of image tokens
        """
        pattern = re.compile(r'\[\[IMAGE:([^\]]+)\]\]')
        return [f"[[IMAGE:{match.group(1)}]]" for match in pattern.finditer(text)]

    async def _render_marp(self, marp_markdown: str) -> str:
        """Render Marp Markdown to PPTX.

        Args:
            marp_markdown: The Marp Markdown content

        Returns:
            Path to the rendered PPTX file
        """
        # For now, just save the markdown
        # TODO: Implement actual Marp rendering
        output_dir = self.data_dir / "intermediates" / self.logger.task_id / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "presentation.pptx"
        # For testing, just create a dummy file
        output_path.write_text("# Mock PPTX content\n", encoding="utf-8")

        return str(output_path)
