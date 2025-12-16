"""Complete PDF to PPTX pipeline orchestration."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.parser.mineru_client import parse_pdf
from app.services.parser.image_manager import create_image_manager
from app.services.llm.split import split_markdown, merge_chunks
from app.services.llm.provider import call_model, batch_call_model
from app.services.renderer.marp_engine import render_marp
from app.services.llm_logger import create_logger

# Import prompt templates
from app.services.llm.prompts import prompt_templates


class PipelineStatus:
    """Status tracking for pipeline execution."""

    PENDING = "pending"
    PARSING = "parsing"
    SPLITTING = "splitting"
    GENERATING_OUTLINE = "generating_outline"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingPipeline:
    """Complete PDF to PPTX processing pipeline."""

    def __init__(self, data_dir: str = "data"):
        """Initialize pipeline.

        Args:
            data_dir: Base data directory
        """
        self.data_dir = Path(data_dir)
        self.image_manager = create_image_manager(data_dir)
        self.status_file = self.data_dir / "processing_status.json"

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def process_pdf(
        self,
        pdf_path: Path,
        presentation_style: str = "academic",
        target_chunks: Optional[int] = 6,
        max_chars: int = 6000,
    ) -> Dict[str, Any]:
        """Process PDF through complete pipeline.

        Args:
            pdf_path: Path to PDF file
            presentation_style: Style (academic, popular, business)
            target_chunks: Target number of chunks after merging
            max_chars: Maximum characters per chunk

        Returns:
            Dictionary with processing results and status
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        try:
            print(f"\n{'='*60}")
            print(f"🚀 Starting pipeline for task: {task_id}")
            print(f"{'='*60}\n")

            # Initialize logger
            logger = create_logger(task_id, self.data_dir / "logs")
            logger.log_summary(f"开始处理 PDF: {pdf_path.name}")

            # Step 1: Create task directory
            task_dir = self.image_manager.create_task_dir(task_id)

            # Step 2: Parse PDF with MinerU
            print(f"\n📄 [Step 1/4] Parsing PDF with MinerU...")
            markdown_path, image_paths, metadata = parse_pdf(
                pdf_path=pdf_path,
                model_version="vlm",
                output_dir=task_dir
            )

            # Save PDF to task directory
            pdf_dest = task_dir / "pdf" / pdf_path.name
            import shutil
            shutil.copy2(pdf_path, pdf_dest)

            print(f"✅ PDF parsed: {markdown_path.name}")
            print(f"   Found {len(image_paths)} images")

            # Step 3: Manage images
            print(f"\n🖼️  [Step 2/4] Managing images...")
            # Check if images are already in the correct location
            expected_images_dir = task_dir / "images"
            image_mapping = {}

            if expected_images_dir.exists() and list(expected_images_dir.glob("*")):
                # Images are already in the right place
                print(f"   Images already in correct location")
                for img_path in image_paths:
                    if img_path.exists():
                        image_mapping[img_path.name] = img_path
            else:
                # Copy images to task directory
                image_mapping = self.image_manager.copy_images(
                    source_paths=image_paths,
                    task_id=task_id,
                    preserve_names=True
                )
            print(f"✅ Managed {len(image_mapping)} images")

            # Step 4: Read and process markdown
            print(f"\n📝 [Step 3/4] Processing content...")
            markdown_content = markdown_path.read_text(encoding="utf-8")

            # Split markdown into chunks
            chunks = split_markdown(markdown_content, max_chars=max_chars)
            print(f"   Split into {len(chunks)} chunks")

            # Merge chunks to target count
            if target_chunks and len(chunks) > target_chunks:
                chunks = merge_chunks(chunks, target_count=target_chunks)
                print(f"   Merged to {len(chunks)} chunks")

            # Save chunks
            chunks_file = task_dir / "chunks.json"
            chunks_file.write_text(
                json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # Step 5: Generate outline with LLM
            print(f"\n🤖 [Step 4a/4] Generating outline with DeepSeek...")

            # Load prompt template
            prompt_template = prompt_templates.STAGE1_PROMPT
            style_name = presentation_style.capitalize()

            # Build prompt with chunks
            full_prompt = prompt_template.format(
                style=style_name,
                content="\n\n".join([f"--- CHUNK {i+1} ---\n{chunk}" for i, chunk in enumerate(chunks)])
            )

            # Call LLM
            # Get model from settings
            from app.core.config import get_settings
            settings = get_settings()
            model_name = settings.llm_model or "deepseek-chat"

            # Log the LLM call
            logger.log_call(
                step_name=f"生成{style_name}风格大纲",
                prompt=full_prompt,
                model=model_name,
                response={},  # Will be filled after call
            )

            response = call_model(
                prompt=full_prompt,
                model=model_name,
                max_tokens=4000,
                temperature=0.7
            )

            # Log the response
            logger.log_call(
                step_name=f"生成{style_name}风格大纲",
                prompt=full_prompt,
                model=model_name,
                response=response,
            )

            outline_md = response["content"]
            print(f"✅ Outline generated ({len(outline_md)} chars)")

            # Save outline
            outline_path = task_dir / "outline.md"
            outline_path.write_text(outline_md, encoding="utf-8")

            # Step 6: Update image paths in outline
            print(f"\n🔗 Updating image paths in outline...")
            updated_outline = self.image_manager.update_markdown_image_paths(
                markdown_content=outline_md,
                task_id=task_id,
                image_mapping=image_mapping
            )

            # Save updated outline
            final_outline_path = task_dir / "markdown" / "final_outline.md"
            final_outline_path.parent.mkdir(exist_ok=True)
            final_outline_path.write_text(updated_outline, encoding="utf-8")
            print(f"✅ Image paths updated")

            # Step 7: Render with Marp
            print(f"\n🎨 [Step 4b/4] Rendering presentation with Marp...")
            output_path = task_dir / "output" / "presentation"

            success = render_marp(
                input_md=final_outline_path,
                output_path=output_path,
                format="pptx"
            )

            if not success:
                raise RuntimeError("Marp rendering failed")

            print(f"✅ Presentation rendered")

            # Compile results
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            result = {
                "task_id": task_id,
                "status": PipelineStatus.COMPLETED,
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_seconds": duration,
                "pdf_path": str(pdf_path),
                "markdown_path": str(markdown_path),
                "outline_path": str(final_outline_path),
                "output_path": str(output_path.with_suffix(".pptx")),
                "image_count": len(image_paths),
                "chunk_count": len(chunks),
                "presentation_style": presentation_style,
                "metadata": metadata,
                "images": [
                    {
                        "original_name": orig,
                        "stored_name": path.name,
                        "url": self.image_manager.get_image_url(task_id, path.name)
                    }
                    for orig, path in image_mapping.items()
                ]
            }

            # Save status
            self._save_status(task_id, result)

            # Log success summary
            logger.log_summary(
                f"""✅ Pipeline 执行成功！

**完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**总耗时**: {duration:.2f}秒
**输出文件**: {output_path.with_suffix('.pptx')}
**图片数量**: {len(image_paths)}
**文本块数量**: {len(chunks)}
**演示风格**: {presentation_style}

**详细结果**:
- PDF 解析: ✅
- 图片管理: ✅
- 文本处理: ✅
- 大纲生成: ✅
- 路径更新: ✅
- 演示渲染: ✅
"""
            )

            print(f"\n{'='*60}")
            print(f"✨ Pipeline completed successfully!")
            print(f"   Task ID: {task_id}")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Output: {output_path.with_suffix('.pptx')}")
            print(f"   Log file: {logger.get_log_path()}")
            print(f"{'='*60}\n")

            return result

        except Exception as e:
            # Save error status
            error_result = {
                "task_id": task_id,
                "status": PipelineStatus.FAILED,
                "started_at": started_at.isoformat(),
                "failed_at": datetime.now().isoformat(),
                "error": str(e),
                "error_type": type(e).__name__,
            }
            self._save_status(task_id, error_result)

            # Log error summary
            try:
                logger.log_summary(
                    f"""❌ Pipeline 执行失败！

**失败时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**错误类型**: {type(e).__name__}
**错误信息**: {str(e)}

**失败原因**:
可能的原因包括：
1. LLM API 调用失败
2. MinerU PDF 解析失败
3. Marp 渲染失败
4. 网络连接问题

**详细错误**:
```
{type(e).__name__}: {str(e)}
```
"""
                )
            except:
                pass  # Ignore logger errors

            print(f"\n❌ Pipeline failed: {e}")
            raise

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get processing status for a task.

        Args:
            task_id: Task identifier

        Returns:
            Status dictionary
        """
        status_file = self.data_dir / f"{task_id}_status.json"

        if not status_file.exists():
            return {
                "task_id": task_id,
                "status": "not_found",
                "message": "Task not found"
            }

        return json.loads(status_file.read_text(encoding="utf-8"))

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get final result for a completed task.

        Args:
            task_id: Task identifier

        Returns:
            Result dictionary or None if not completed
        """
        status = self.get_status(task_id)

        if status.get("status") != PipelineStatus.COMPLETED:
            return None

        return status

    def _save_status(self, task_id: str, status: Dict[str, Any]) -> None:
        """Save status to file.

        Args:
            task_id: Task identifier
            status: Status dictionary
        """
        status_file = self.data_dir / f"{task_id}_status.json"
        status_file.write_text(
            json.dumps(status, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def cleanup_old_tasks(self, keep_days: int = 7) -> List[str]:
        """Clean up old task files.

        Args:
            keep_days: Number of days to keep tasks

        Returns:
            List of deleted task IDs
        """
        import time
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=keep_days)
        cutoff_timestamp = cutoff.timestamp()

        deleted_tasks = []

        # Check all status files
        for status_file in self.data_dir.glob("*_status.json"):
            try:
                stat = status_file.stat()
                if stat.st_mtime < cutoff_timestamp:
                    # Extract task ID from filename
                    task_id = status_file.stem.replace("_status", "")

                    # Delete entire task directory
                    task_dir = self.data_dir / task_id
                    if task_dir.exists():
                        import shutil
                        shutil.rmtree(task_dir)

                    # Delete status file
                    status_file.unlink()

                    deleted_tasks.append(task_id)
                    print(f"🗑️  Cleaned up task: {task_id}")

            except Exception as e:
                print(f"Warning: Failed to cleanup {status_file}: {e}")

        return deleted_tasks

    def process_pdf_with_workflow(
        self,
        pdf_path: Path | str,
        presentation_style: str = "academic",
        target_chunks: Optional[int] = 6,
        max_chars: int = 6000,
    ) -> Dict[str, Any]:
        """Process PDF using the new WorkflowOrchestrator.

        This method uses the improved workflow with:
        - Split → Stage1 Loop → Merge → Stage2 → Render

        Args:
            pdf_path: Path to PDF file
            presentation_style: Style (academic, popular, business)
            target_chunks: Target number of chunks after merging
            max_chars: Maximum characters per chunk

        Returns:
            Dictionary with processing results and status
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]
        started_at = datetime.now()

        try:
            print(f"\n{'='*60}")
            print(f"🚀 Starting NEW WORKFLOW for task: {task_id}")
            print(f"{'='*60}\n")

            # Initialize logger
            logger = create_logger(task_id, self.data_dir / "logs")

            # Initialize workflow orchestrator
            workflow = WorkflowOrchestrator(data_dir=str(self.data_dir), logger=logger)

            # Execute workflow
            import asyncio
            result = asyncio.run(workflow.execute_full_workflow(
                pdf_path=str(pdf_path) if isinstance(pdf_path, Path) else pdf_path,
                presentation_style=presentation_style,
                max_chars=max_chars,
                target_chunks=target_chunks
            ))

            # Calculate duration
            duration = (datetime.now() - started_at).total_seconds()

            print(f"\n{'='*60}")
            print(f"✨ Pipeline completed successfully!")
            print(f"   Task ID: {task_id}")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Output: {result.get('output_path', 'N/A')}")
            print(f"{'='*60}\n")

            return {
                "status": "success",
                "task_id": task_id,
                "duration": duration,
                "output_path": result.get("output_path"),
                "chunks_count": result.get("chunks_count", 0),
                "presentation_style": presentation_style,
                "result": result
            }

        except Exception as e:
            duration = (datetime.now() - started_at).total_seconds()
            error_msg = f"Pipeline failed: {str(e)}"

            print(f"\n❌ {error_msg}")
            print(f"Duration: {duration:.2f}s")

            # Log error
            logger = create_logger(task_id, self.data_dir / "logs")
            logger.log_summary(f"❌ {error_msg}")

            return {
                "status": "failed",
                "task_id": task_id,
                "error": error_msg,
                "duration": duration
            }


def process_pdf(
    pdf_path: Path,
    presentation_style: str = "academic",
    target_chunks: Optional[int] = 6,
    data_dir: str = "data",
) -> Dict[str, Any]:
    """Process PDF through complete pipeline.

    This is the main entry point for pipeline processing.

    Args:
        pdf_path: Path to PDF file
        presentation_style: Style (academic, popular, business)
        target_chunks: Target number of chunks
        data_dir: Data directory

    Returns:
        Processing results
    """
    pipeline = ProcessingPipeline(data_dir)
    return pipeline.process_pdf(
        pdf_path=pdf_path,
        presentation_style=presentation_style,
        target_chunks=target_chunks
    )
