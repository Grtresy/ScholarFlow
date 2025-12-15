"""
FastAPI endpoints for file upload operations.

Since LangGraph doesn't handle file uploads directly, we use FastAPI to:
1. Accept PDF uploads from the React frontend
2. Save PDFs to the local filesystem
3. Return the file path and task ID to start the workflow
"""

import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

# Create router
router = APIRouter(prefix="/api", tags=["upload"])

# Directory for uploaded PDFs
UPLOAD_DIR = "data/inputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Directory for generated presentations
OUTPUT_DIR = "data/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class UploadResponse(BaseModel):
    """Response model for file upload."""
    task_id: str
    pdf_path: str
    message: str
    timestamp: str


class DownloadResponse(BaseModel):
    """Response model for file download."""
    file_path: str
    task_id: str
    filename: str


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file and return task ID and file path.

    Args:
        file: PDF file to upload

    Returns:
        UploadResponse: Contains task_id, pdf_path, and timestamp

    Raises:
        HTTPException: If file is not a PDF
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    try:
        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{task_id}_{file.filename}"
        pdf_path = os.path.join(UPLOAD_DIR, safe_filename)

        # Save file
        with open(pdf_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return UploadResponse(
            task_id=task_id,
            pdf_path=pdf_path,
            message="PDF uploaded successfully",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.get("/download/{task_id}")
async def download_result(task_id: str):
    """
    Download the generated presentation file.

    Args:
        task_id: Task ID from the workflow

    Returns:
        FileResponse: The generated presentation file

    Raises:
        HTTPException: If file not found
    """
    # Try to find the output file
    # The exact filename depends on how the workflow saves files
    # For now, we'll look for any file with the task_id in OUTPUT_DIR
    for filename in os.listdir(OUTPUT_DIR):
        if task_id in filename:
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.isfile(file_path):
                return FileResponse(
                    path=file_path,
                    filename=filename,
                    media_type="application/octet-stream"
                )

    raise HTTPException(
        status_code=404,
        detail=f"No result found for task_id: {task_id}"
    )


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    Delete task files (uploaded PDF and generated outputs).

    Args:
        task_id: Task ID to delete

    Returns:
        dict: Success message
    """
    deleted_files = []

    # Delete uploaded PDF
    for filename in os.listdir(UPLOAD_DIR):
        if task_id in filename:
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)

    # Delete generated outputs
    for filename in os.listdir(OUTPUT_DIR):
        if task_id in filename:
            file_path = os.path.join(OUTPUT_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)

    return {
        "task_id": task_id,
        "deleted_files": deleted_files,
        "message": f"Deleted {len(deleted_files)} files"
    }
