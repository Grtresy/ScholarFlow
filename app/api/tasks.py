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
from app.services.llm.prompts.prompt_templates import save_custom_templates
from app.storage.checkpointer import get_checkpointer

router = APIRouter(prefix="/api", tags=["tasks"])


# ===== Request Models =====


class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""

    pdf_path: str = Field(..., description="Path to the PDF file")
    presentation_style: str = Field(
        default="academic",
        description="Presentation style: academic, popular, business, or computational_thinking",
    )
    max_chars: int = Field(default=8000, description="Maximum characters per chunk")
    target_chunks: int = Field(default=3, description="Target number of chunks")
    output_format: str = Field(default="pptx", description="Output format: pptx, pdf, or html")
    enable_human_review: bool = Field(default=True, description="Enable human review")
    custom_stage1_prompt: Optional[str] = Field(None, description="Custom Stage 1 prompt template")
    custom_stage2_prompt: Optional[str] = Field(None, description="Custom Stage 2 prompt template")


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
    user_modifications: str = ""


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
            f"Use: academic, popular, business, or computational_thinking",
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

    # Save custom prompts if provided
    if request.custom_stage1_prompt or request.custom_stage2_prompt:
        save_custom_templates(
            task_id=task_id,
            stage1_template=request.custom_stage1_prompt,
            stage2_template=request.custom_stage2_prompt,
        )

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

    # Immediately update status to prevent race condition
    # Frontend polls immediately, so we must update status before background task runs
    if feedback.approved:
        new_status = TaskStatus.STAGE2_PROCESSING.value
        current_step = "审核通过，准备进入Stage 2"
    elif feedback.action == "regenerate":
        new_status = TaskStatus.STAGE1_PROCESSING.value
        current_step = "准备重新生成"
    elif feedback.action == "abort":
        new_status = TaskStatus.FAILED.value
        current_step = "任务被用户终止"
    else:
        new_status = TaskStatus.STAGE2_PROCESSING.value
        current_step = "处理中"
    
    state["status"] = new_status
    state["needs_human_review"] = False
    state["current_step"] = current_step
    state["updated_at"] = datetime.now().isoformat()
    checkpointer.save_state(task_id, state, "feedback_received")

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


# ===== Markdown Content Endpoints =====


class SaveMarkdownRequest(BaseModel):
    """Request model for saving markdown content."""
    content: str = Field(..., description="Markdown content")
    stage: str = Field(default="marp_markdown", description="Stage: merged_outline or marp_markdown")


@router.get("/tasks/{task_id}/markdown")
async def get_markdown_content(task_id: str, stage: Optional[str] = None):
    """Get markdown content for a task.

    Args:
        task_id: Task identifier
        stage: Optional stage filter ('merged_outline' or 'marp_markdown')
    """
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    if stage == "merged_outline":
        content = state.get("merged_outline", "")
    elif stage == "marp_markdown":
        content = state.get("marp_markdown", "")
    else:
        # Return latest available markdown
        content = state.get("marp_markdown") or state.get("merged_outline", "")
        stage = "marp_markdown" if state.get("marp_markdown") else "merged_outline"

    return {
        "task_id": task_id,
        "content": content,
        "stage": stage,
        "updated_at": state.get("updated_at"),
    }


@router.post("/tasks/{task_id}/markdown")
async def save_markdown_content(
    task_id: str,
    request: SaveMarkdownRequest,
    background_tasks: BackgroundTasks,
):
    """Save edited markdown content.

    Args:
        task_id: Task identifier
        request: SaveMarkdownRequest with content and stage
    """
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    content = request.content
    stage = request.stage

    # Update state with new content
    if stage == "merged_outline":
        state["merged_outline"] = content
    elif stage == "marp_markdown":
        state["marp_markdown"] = content

    state["updated_at"] = datetime.now().isoformat()
    checkpointer.save_state(task_id, state, "markdown_updated")

    # Trigger re-render if in completed state
    if state.get("status") == TaskStatus.COMPLETED.value:
        background_tasks.add_task(rerender_presentation, task_id, content)

    return {
        "status": "success",
        "message": "Markdown saved",
        "task_id": task_id,
    }


async def rerender_presentation(task_id: str, markdown: str):
    """Background task to re-render presentation with updated markdown."""
    # TODO: Implement re-rendering logic
    # This would involve calling the Marp renderer with the new markdown
    pass
