"""v2 API routes for task management."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.graph.state import (
    PresentationStyle,
    TaskStatus,
    WorkflowState,
    create_initial_state,
)
from app.graph.workflow import resume_workflow, run_workflow
from app.storage.checkpointer import get_checkpointer

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ===== Request Models =====


class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""

    pdf_path: str = Field(..., description="Path to the PDF file")
    presentation_style: str = Field(
        default="academic",
        description="Presentation style: academic, popular, or business",
    )
    max_chars: int = Field(default=6000, description="Maximum characters per chunk")
    target_chunks: int = Field(default=6, description="Target number of chunks")
    output_format: str = Field(default="pptx", description="Output format: pptx, pdf, or html")
    enable_human_review: bool = Field(default=True, description="Enable human review")


class HumanFeedbackRequest(BaseModel):
    """Request model for human feedback."""

    approved: bool = Field(..., description="Whether the content is approved")
    action: Optional[str] = Field(
        None,
        description="Action: 'regenerate' to redo, 'abort' to cancel",
    )
    comments: Optional[str] = Field(None, description="Optional comments")
    modifications: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional modifications",
    )


# ===== Response Models =====


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str
    status: str
    progress_percentage: float
    current_step: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    needs_human_review: bool = False
    review_points: List[Dict[str, Any]] = []


class TaskResultResponse(BaseModel):
    """Response model for task result."""

    task_id: str
    status: str
    pdf_path: str
    output_path: Optional[str] = None
    markdown_path: Optional[str] = None
    chunks_count: int = 0
    stage1_completed: int = 0
    presentation_style: str
    created_at: str
    updated_at: str


class TaskListResponse(BaseModel):
    """Response model for task list."""

    tasks: List[Dict[str, Any]]
    total: int


# ===== Background Task Runner =====


async def run_workflow_background(task_id: str, initial_state: WorkflowState):
    """Run workflow in background."""
    try:
        await run_workflow(initial_state, thread_id=task_id)
    except Exception as e:
        # Update state with error
        checkpointer = get_checkpointer()
        state = checkpointer.load_state(task_id)
        if state:
            state["status"] = TaskStatus.FAILED.value
            state["error_message"] = str(e)
            state["updated_at"] = datetime.now().isoformat()
            checkpointer.save_state(task_id, state, "error")


# ===== API Endpoints =====


@router.post("/tasks", response_model=TaskStatusResponse)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
):
    """Create a new processing task.

    This endpoint creates a new task and starts processing in the background.
    Returns immediately with task ID for status polling.
    """
    # Generate task ID
    task_id = str(uuid.uuid4())[:8]

    # Validate presentation style
    try:
        style = PresentationStyle(request.presentation_style)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid presentation style: {request.presentation_style}. "
            f"Use: academic, popular, or business",
        )

    # Create initial state
    initial_state = create_initial_state(
        task_id=task_id,
        pdf_path=request.pdf_path,
        presentation_style=style.value,
        max_chars=request.max_chars,
        target_chunks=request.target_chunks,
        output_format=request.output_format,
        enable_human_review=request.enable_human_review,
    )

    # Save initial state
    checkpointer = get_checkpointer()
    checkpointer.save_state(task_id, initial_state, "create")

    # Start workflow in background
    background_tasks.add_task(run_workflow_background, task_id, initial_state)

    return TaskStatusResponse(
        task_id=task_id,
        status=TaskStatus.PENDING.value,
        progress_percentage=0.0,
        current_step="任务已创建",
        created_at=initial_state["created_at"],
        updated_at=initial_state["updated_at"],
        needs_human_review=request.enable_human_review,
    )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get task status by ID."""
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return TaskStatusResponse(
        task_id=state.get("task_id", task_id),
        status=state.get("status", TaskStatus.PENDING.value),
        progress_percentage=state.get("progress_percentage", 0.0),
        current_step=state.get("current_step", ""),
        created_at=state.get("created_at", ""),
        updated_at=state.get("updated_at", ""),
        error_message=state.get("error_message"),
        needs_human_review=state.get("needs_human_review", False),
        review_points=state.get("review_points", []),
    )


@router.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """Get task result by ID."""
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return TaskResultResponse(
        task_id=state.get("task_id", task_id),
        status=state.get("status", TaskStatus.PENDING.value),
        pdf_path=state.get("pdf_path", ""),
        output_path=state.get("output_path"),
        markdown_path=state.get("markdown_path"),
        chunks_count=state.get("chunks_count", 0),
        stage1_completed=state.get("stage1_completed", 0),
        presentation_style=state.get("presentation_style", "academic"),
        created_at=state.get("created_at", ""),
        updated_at=state.get("updated_at", ""),
    )


@router.post("/tasks/{task_id}/human-feedback")
async def submit_human_feedback(
    task_id: str,
    feedback: HumanFeedbackRequest,
    background_tasks: BackgroundTasks,
):
    """Submit human feedback for a task in review state."""
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if state.get("status") != TaskStatus.HUMAN_REVIEW.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not in review state. Current status: {state.get('status')}",
        )

    # Prepare feedback dict
    feedback_dict = {
        "approved": feedback.approved,
        "action": feedback.action,
        "comments": feedback.comments,
        "modifications": feedback.modifications,
        "timestamp": datetime.now().isoformat(),
    }

    # Resume workflow with feedback
    background_tasks.add_task(resume_workflow, task_id, feedback_dict)

    return {
        "status": "success",
        "message": "Feedback submitted, workflow resuming",
        "task_id": task_id,
    }


@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: str,
    background_tasks: BackgroundTasks,
):
    """Resume a paused task."""
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    status = state.get("status", "")
    if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume task with status: {status}",
        )

    # Resume workflow
    background_tasks.add_task(resume_workflow, task_id, None)

    return {
        "status": "success",
        "message": "Task resuming",
        "task_id": task_id,
    }


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
):
    """List all tasks with optional status filter."""
    checkpointer = get_checkpointer()

    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}",
            )

    tasks = checkpointer.list_tasks(status=status_enum, limit=limit)

    return TaskListResponse(tasks=tasks, total=len(tasks))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # Only allow deletion of completed or failed tasks
    status = state.get("status", "")
    if status not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete task with status: {status}. Cancel it first.",
        )

    if checkpointer.delete_task(task_id):
        return {"status": "success", "message": f"Task {task_id} deleted"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete task")


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    status = state.get("status", "")
    if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
        raise HTTPException(
            status_code=400,
            detail=f"Task already {status}, cannot cancel",
        )

    # Update state to failed
    state["status"] = TaskStatus.FAILED.value
    state["error_message"] = "Task cancelled by user"
    state["current_step"] = "任务被用户取消"
    state["updated_at"] = datetime.now().isoformat()

    checkpointer.save_state(task_id, state, "cancel")

    return {"status": "success", "message": f"Task {task_id} cancelled"}
