"""Rendering node for workflow."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState
from app.services.renderer.marp_engine import MarpEngine
from app.services.parser.image_manager import ImageManager


def node_render(state: WorkflowState) -> Dict[str, Any]:
    """Render Marp Markdown to presentation format.

    This node:
    - Takes the Marp Markdown
    - Calls MarpEngine to render to output format
    - Returns the final output path

    Args:
        state: Current workflow state
    
    Returns:
        State updates with output_path
    """
    marp_markdown = state.get("marp_markdown", "")
    marp_markdown_path = state.get("marp_markdown_path", "")
    output_format = state.get("output_format", "pptx")
    task_id = state.get("task_id", "unknown")

    # Get token map for restoration
    image_token_map = state.get("image_token_map", {})

    # Fallback: try to load token map from file if not in state
    if not image_token_map and task_id:
        import json
        import warnings
        warnings.warn(
            f"⚠️ image_token_map not found in state for task {task_id}. "
            "This indicates a state flow issue. Loaded from file as fallback.",
            UserWarning,
            stacklevel=2
        )
        token_map_path = Path("data/workflow/intermediate") / task_id / "token_map.json"
        if token_map_path.exists():
            try:
                with open(token_map_path, 'r', encoding='utf-8') as f:
                    image_token_map = json.load(f)
                print(f"📋 Loaded token map from file: {len(image_token_map)} tokens")
            except Exception as e:
                print(f"⚠️ Failed to load token map: {e}")

    if not marp_markdown and not marp_markdown_path:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "No Marp Markdown to render",
            "current_step": "渲染失败：没有Marp Markdown",
        }

    try:
        # Restore tokens to proper image links before rendering
        if image_token_map:
            image_manager = ImageManager(Path("data/workflow/intermediate"))
            marp_markdown = image_manager.restore_tokens_to_markdown_enhanced(
                tokenized_content=marp_markdown,
                token_map=image_token_map,
                output_format='marp'
            )

        # Ensure markdown file exists and contains restored tokens
        if marp_markdown_path:
            input_md = Path(marp_markdown_path)
            # Write restored content back to the file
            input_md.write_text(marp_markdown, encoding="utf-8")
        else:
            # Save markdown to file first
            output_dir = Path("data/workflow/intermediate") / task_id
            output_dir.mkdir(parents=True, exist_ok=True)
            input_md = output_dir / "presentation.md"
            input_md.write_text(marp_markdown, encoding="utf-8")

        if not input_md.exists():
            return {
                "status": TaskStatus.FAILED.value,
                "error_message": f"Marp Markdown file not found: {input_md}",
                "current_step": "渲染失败：Markdown文件不存在",
            }

        # Prepare output path
        output_dir = Path("data/workflow/output") / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_base = output_dir / "presentation"

        # Initialize Marp engine and render
        engine = MarpEngine()
        success = engine.render(
            input_md=input_md,
            output_path=output_base,
            format=output_format,
        )

        if success:
            output_path = output_base.with_suffix(f".{output_format}")

            # Log success
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": "rendering_complete",
                "format": output_format,
                "output_path": str(output_path),
            }
            execution_log = state.get("execution_log", [])
            execution_log.append(log_entry)

            return {
                "status": TaskStatus.COMPLETED.value,
                "output_path": str(output_path),
                "current_step": f"渲染完成：{output_path.name}",
                "progress_percentage": 100.0,
                "updated_at": datetime.now().isoformat(),
                "execution_log": execution_log,
            }
        else:
            return {
                "status": TaskStatus.FAILED.value,
                "error_message": "Marp rendering failed",
                "current_step": "渲染失败：Marp CLI返回错误",
            }

    except FileNotFoundError as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"Marp or Chrome not found: {e}",
            "current_step": f"渲染失败：{e}",
        }
    except Exception as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"Rendering failed: {e}",
            "current_step": f"渲染失败：{e}",
        }
