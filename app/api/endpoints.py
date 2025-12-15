"""API endpoints for PDF to PPTX processing."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.pipeline import ProcessingPipeline, PipelineStatus
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["processing"])

# Initialize pipeline
settings = get_settings()
pipeline = ProcessingPipeline(data_dir=str(settings.data_dir) if settings.data_dir else "data")


# Request/Response Models
class ProcessRequest(BaseModel):
    presentation_style: str = Field(default="academic", description="Presentation style: academic, popular, business")
    target_chunks: Optional[int] = Field(default=6, description="Target number of chunks after merging")
    max_chars: int = Field(default=6000, description="Maximum characters per chunk")


class ProcessResponse(BaseModel):
    task_id: str
    status: str
    message: str
    pdf_path: Optional[str] = None


class StatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    message: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


class ResultResponse(BaseModel):
    task_id: str
    status: str
    output_path: Optional[str] = None
    outline_path: Optional[str] = None
    image_count: Optional[int] = None
    chunk_count: Optional[int] = None
    presentation_style: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/upload", response_model=ProcessResponse)
async def upload_and_process(
    file: UploadFile = File(...),
    presentation_style: str = "academic",
    target_chunks: Optional[int] = 6,
    max_chars: int = 6000,
):
    """Upload a PDF file and start processing pipeline.

    Args:
        file: PDF file to upload
        presentation_style: Presentation style (academic, popular, business)
        target_chunks: Target number of chunks
        max_chars: Maximum characters per chunk

    Returns:
        Task information with task_id
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save uploaded file
    upload_dir = Path(settings.data_dir or "data") / "uploads" if settings.data_dir else Path("data") / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Start processing in background (for now, process synchronously for simplicity)
    # In production, use a task queue like Celery or RQ
    try:
        result = pipeline.process_pdf(
            pdf_path=file_path,
            presentation_style=presentation_style,
            target_chunks=target_chunks,
            max_chars=max_chars,
        )

        return ProcessResponse(
            task_id=result["task_id"],
            status=result["status"],
            message="Processing completed successfully",
            pdf_path=str(file_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """Get processing status for a task.

    Args:
        task_id: Task identifier

    Returns:
        Current status information
    """
    status_info = pipeline.get_status(task_id)

    if status_info.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return StatusResponse(
        task_id=status_info.get("task_id", task_id),
        status=status_info.get("status", "unknown"),
        message=_get_status_message(status_info.get("status")),
        started_at=status_info.get("started_at"),
        completed_at=status_info.get("completed_at") or status_info.get("failed_at"),
        duration_seconds=status_info.get("duration_seconds"),
        error=status_info.get("error"),
    )


@router.get("/result/{task_id}", response_model=ResultResponse)
async def get_result(task_id: str):
    """Get final result for a completed task.

    Args:
        task_id: Task identifier

    Returns:
        Processing results
    """
    result = pipeline.get_result(task_id)

    if result is None:
        status_info = pipeline.get_status(task_id)
        if status_info.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        else:
            raise HTTPException(status_code=409, detail=f"Task {task_id} is not yet completed (status: {status_info.get('status')})")

    return ResultResponse(
        task_id=result["task_id"],
        status=result["status"],
        output_path=result.get("output_path"),
        outline_path=result.get("outline_path"),
        image_count=result.get("image_count"),
        chunk_count=result.get("chunk_count"),
        presentation_style=result.get("presentation_style"),
        metadata=result.get("metadata"),
    )


@router.get("/download/{task_id}")
async def download_result(task_id: str):
    """Download the generated PPTX file.

    Args:
        task_id: Task identifier

    Returns:
        PPTX file
    """
    result = pipeline.get_result(task_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found or not completed")

    output_path = result.get("output_path")
    if not output_path or not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"presentation_{task_id}.pptx",
        headers={"Content-Disposition": f"attachment; filename=presentation_{task_id}.pptx"}
    )


@router.get("/markdown/{task_id}")
async def get_markdown(task_id: str):
    """Get the generated Markdown outline.

    Args:
        task_id: Task identifier

    Returns:
        Markdown content
    """
    status_info = pipeline.get_status(task_id)

    if status_info.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    outline_path = status_info.get("outline_path")
    if not outline_path or not Path(outline_path).exists():
        raise HTTPException(status_code=404, detail="Markdown outline not found")

    return FileResponse(
        path=outline_path,
        media_type="text/markdown",
        filename=f"outline_{task_id}.md"
    )


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Delete a task and all its files.

    Args:
        task_id: Task identifier

    Returns:
        Deletion status
    """
    status_info = pipeline.get_status(task_id)

    if status_info.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Delete task files
    data_dir = Path(settings.data_dir or "data")
    task_dir = data_dir / task_id
    status_file = data_dir / f"{task_id}_status.json"

    if task_dir.exists():
        shutil.rmtree(task_dir)

    if status_file.exists():
        status_file.unlink()

    return {"status": "success", "message": f"Task {task_id} deleted"}


@router.post("/cleanup")
async def cleanup_old_tasks(keep_days: int = 7):
    """Clean up old task files.

    Args:
        keep_days: Number of days to keep tasks

    Returns:
        List of deleted task IDs
    """
    deleted_tasks = pipeline.cleanup_old_tasks(keep_days=keep_days)

    return {
        "status": "success",
        "message": f"Cleaned up {len(deleted_tasks)} old tasks",
        "deleted_tasks": deleted_tasks
    }


def _get_status_message(status: str) -> str:
    """Get human-readable status message.

    Args:
        status: Status string

    Returns:
        Human-readable message
    """
    messages = {
        PipelineStatus.PENDING: "Task queued",
        PipelineStatus.PARSING: "Parsing PDF with MinerU",
        PipelineStatus.SPLITTING: "Splitting and processing content",
        PipelineStatus.GENERATING_OUTLINE: "Generating outline with LLM",
        PipelineStatus.RENDERING: "Rendering presentation with Marp",
        PipelineStatus.COMPLETED: "Processing completed",
        PipelineStatus.FAILED: "Processing failed",
        "not_found": "Task not found",
    }

    return messages.get(status, f"Unknown status: {status}")

