"""Error handling node for workflow."""

from datetime import datetime
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState


def node_handle_error(state: WorkflowState) -> Dict[str, Any]:
    """Handle errors and implement retry logic.

    This node:
    - Checks retry count
    - Determines if retry is possible
    - Updates state for retry or failure

    Args:
        state: Current workflow state

    Returns:
        State updates for retry or failure
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    error_message = state.get("error_message", "Unknown error")
    status = state.get("status", TaskStatus.FAILED.value)

    # Log error
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "error_handling",
        "error": error_message,
        "retry_count": retry_count,
        "max_retries": max_retries,
    }
    execution_log = state.get("execution_log", [])
    execution_log.append(log_entry)

    if retry_count < max_retries:
        # Can retry - reset to parsing stage
        return {
            "status": TaskStatus.PARSING.value,
            "retry_count": retry_count + 1,
            "error_message": "",
            "current_step": f"重试 {retry_count + 1}/{max_retries}",
            "progress_percentage": 5.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }
    else:
        # Max retries reached
        return {
            "status": TaskStatus.FAILED.value,
            "retry_count": retry_count,
            "error_message": f"Maximum retries ({max_retries}) exceeded. Last error: {error_message}",
            "current_step": f"任务失败：重试{max_retries}次后仍然失败",
            "progress_percentage": 0.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }
