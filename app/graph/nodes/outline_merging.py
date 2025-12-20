"""Outline merging node for workflow."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState
from app.services.llm.merge import merge_outlines


def node_merge_outlines(state: WorkflowState) -> Dict[str, Any]:
    """Merge Stage 1 results into unified outline.

    This node:
    - Collects all Stage 1 results
    - Merges outlines by chunk order
    - Saves merged outline

    Args:
        state: Current workflow state

    Returns:
        State updates with merged_outline
    """
    stage1_results = state.get("stage1_results", [])
    task_id = state.get("task_id", "unknown")

    if not stage1_results:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "No Stage 1 results to merge",
            "current_step": "合并失败：没有Stage 1结果",
        }

    # Filter successful results
    successful_results = [r for r in stage1_results if r.get("success", False)]

    if not successful_results:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "All Stage 1 processing failed",
            "current_step": "合并失败：所有Stage 1处理均失败",
        }

    try:
        # Merge outlines
        merged = merge_outlines(successful_results)

        # Save merged outline
        output_dir = Path("data/workflow/intermediate") / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        outline_path = output_dir / "merged_outline.md"
        outline_path.write_text(merged, encoding="utf-8")

        # Log success
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "outline_merging",
            "message": f"Merged {len(successful_results)} outlines",
            "outline_length": len(merged),
            "failed_chunks": len(stage1_results) - len(successful_results),
        }
        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)

        # Determine if human review is needed
        needs_review = state.get("needs_human_review", True)

        if needs_review:
            # Prepare review point
            review_point = {
                "type": "outline_review",
                "node": "merge_outlines",
                "content": merged,
                "prompt": "请审核合并后的大纲。您可以：\n1. 批准通过\n2. 要求重新生成\n3. 提供修改建议",
                "timestamp": datetime.now().isoformat(),
            }

            return {
                "status": TaskStatus.HUMAN_REVIEW.value,
                "merged_outline": merged,
                "merged_outline_path": str(outline_path),
                "review_points": [review_point],
                "current_step": "等待审核合并后的大纲",
                "progress_percentage": 55.0,
                "updated_at": datetime.now().isoformat(),
                "execution_log": execution_log,
            }
        else:
            # Skip human review
            return {
                "status": TaskStatus.STAGE2_PROCESSING.value,
                "merged_outline": merged,
                "merged_outline_path": str(outline_path),
                "approved": True,
                "current_step": "大纲合并完成，进入Stage 2",
                "progress_percentage": 60.0,
                "updated_at": datetime.now().isoformat(),
                "execution_log": execution_log,
            }

    except Exception as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"Outline merging failed: {e}",
            "current_step": f"大纲合并失败：{e}",
        }
