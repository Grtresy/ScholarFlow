"""Human review nodes for workflow."""

from datetime import datetime
from typing import Any, Dict, Literal

from langgraph.types import Command

from app.graph.state import TaskStatus, WorkflowState


def node_human_review(state: WorkflowState) -> Dict[str, Any]:
    """Prepare state for human review.

    This node is triggered when human review is needed.
    It sets up the review context and pauses for human input.

    Args:
        state: Current workflow state

    Returns:
        State updates with review setup
    """
    # The state should already have review_points set by the previous node
    review_points = state.get("review_points", [])

    if not review_points:
        # No review needed, continue
        return {
            "status": TaskStatus.STAGE2_PROCESSING.value,
            "needs_human_review": False,
            "approved": True,
            "current_step": "无需审核，继续处理",
        }

    # Update status for human review
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "human_review_requested",
        "review_type": review_points[0].get("type", "unknown"),
    }
    execution_log = state.get("execution_log", [])
    execution_log.append(log_entry)

    # Note: LangGraph will automatically save state before interrupt
    # No manual persistence needed
    result = {
        "status": TaskStatus.HUMAN_REVIEW.value,
        "needs_human_review": True,
        "current_step": "等待人工审核",
        "updated_at": datetime.now().isoformat(),
        "execution_log": execution_log,
    }
    # LangGraph会在到达process_feedback前自动中断并保存状态，无需手动保存
    return result


def node_process_feedback(state: WorkflowState) -> Dict[str, Any]:
    """Process human feedback and determine next action.

    This node is called after human provides feedback.
    It routes to the appropriate next step based on feedback.

    Args:
        state: Current workflow state with human_feedback

    Returns:
        State updates based on feedback
    """
    # When using Command(resume=...), the resume value is in the state
    # Handle both direct human_feedback and Command resume
    feedback_data = state.get("human_feedback", {})
    # If Command was used with resume, the resume value is directly the feedback dict
    if not feedback_data and isinstance(state.get("input"), dict):
        # Check if input contains the feedback (from Command resume)
        potential_feedback = state.get("input", {})
        if isinstance(potential_feedback, dict) and "action" in potential_feedback:
            feedback_data = potential_feedback
    # Fallback: also check if input itself is the feedback
    if not feedback_data and isinstance(state.get("input"), dict):
        input_data = state.get("input", {})
        if isinstance(input_data, dict) and any(k in input_data for k in ["action", "approved", "comments"]):
            feedback_data = input_data

    approved = feedback_data.get("approved", False)
    action = feedback_data.get("action", "")
    comments = feedback_data.get("comments", "")

    # Log feedback
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "human_feedback_received",
        "approved": approved,
        "action": action,
        "has_comments": bool(comments),
    }
    execution_log = state.get("execution_log", [])
    execution_log.append(log_entry)

    if approved:
        # Approved - continue to Stage 2
        result = {
            "status": TaskStatus.STAGE2_PROCESSING.value,
            "approved": True,
            "needs_human_review": False,
            "review_points": [],
            "current_step": "审核通过，进入Stage 2",
            "progress_percentage": 60.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }
        return result
    elif action == "regenerate":
        # Request to regenerate - go back to Stage 1
        result = {
            "status": TaskStatus.STAGE1_PROCESSING.value,
            "approved": False,
            "needs_human_review": False,
            "review_points": [],
            "current_chunk_index": 0,
            "stage1_results": [],
            "stage1_completed": 0,
            "merged_outline": "",
            "current_step": "根据反馈重新生成大纲",
            "progress_percentage": 20.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }
        return result
    elif action == "abort":
        # Abort the task
        result = {
            "status": TaskStatus.FAILED.value,
            "approved": False,
            "error_message": f"Task aborted by user. Reason: {comments}",
            "current_step": "任务被用户终止",
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }
        return result
    else:
        # 未定义的操作，结束任务
        result = {
            "status": TaskStatus.FAILED.value,
            "approved": False,
            "error_message": f"未知的反馈操作: {action}",
            "current_step": "任务因未知操作而结束",
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }
        return result


def route_after_feedback(state: WorkflowState) -> Literal["stage1", "stage2", "end"]:
    """Route based on human feedback result.

    Args:
        state: Current workflow state

    Returns:
        Next node to execute
    """
    status = state.get("status", "")

    if status == TaskStatus.STAGE2_PROCESSING.value:
        return "stage2"
    elif status == TaskStatus.STAGE1_PROCESSING.value:
        return "stage1"
    else:
        return "end"
