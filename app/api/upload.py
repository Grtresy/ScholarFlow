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
UPLOAD_DIR = "data/upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Directory for generated presentations
OUTPUT_DIR = "data/workflow/output"
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

    This endpoint will:
    1. Load the latest markdown from workflow state
    2. Re-render the presentation with current markdown
    3. Return the generated file

    Args:
        task_id: Task ID from the workflow

    Returns:
        FileResponse: The generated presentation file

    Raises:
        HTTPException: If file not found or rendering fails
    """
    import tempfile
    from pathlib import Path
    from app.storage.checkpointer import get_checkpointer
    from app.services.renderer.marp_engine import MarpEngine
    from app.services.parser.image_manager import ImageManager

    # Load workflow state
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    # Get the latest markdown content
    marp_markdown = state.get("marp_markdown", "")
    if not marp_markdown:
        raise HTTPException(
            status_code=404,
            detail=f"No markdown content found for task: {task_id}"
        )

    # Get output format
    output_format = state.get("output_format", "pptx")

    try:
        # Get token map for image restoration
        image_token_map = state.get("image_token_map", {})

        # Restore tokens if token map exists
        if image_token_map:
            image_manager = ImageManager(Path("data/workflow/intermediate"))
            marp_markdown = image_manager.restore_tokens_to_markdown_enhanced(
                tokenized_content=marp_markdown,
                token_map=image_token_map,
                output_format='marp'
            )

        # Use intermediate directory for markdown (for correct image paths)
        intermediate_dir = Path("data/workflow/intermediate") / task_id
        intermediate_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        input_md = intermediate_dir / f"{timestamp}.md"

        # Save markdown to file
        input_md.write_text(marp_markdown, encoding='utf-8')

        # Output to output directory
        output_dir = Path("data/workflow/output") / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_base = output_dir / timestamp

        try:
            # Render markdown to presentation format
            engine = MarpEngine()
            success = engine.render(
                input_md=input_md,
                output_path=output_base,
                format=output_format,
            )

            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to render presentation"
                )

            # Get the generated file path
            presentation_file = output_base.with_suffix(f".{output_format}")

            if not presentation_file.exists():
                raise HTTPException(
                    status_code=500,
                    detail="Rendered file not found"
                )

            # Generate filename for download
            filename = f'presentation_{task_id}_{timestamp}.{output_format}'

            return FileResponse(
                path=str(presentation_file),
                filename=filename,
                media_type="application/octet-stream"
            )
        except HTTPException:
            raise
        # Keep markdown and pptx files for version history (no cleanup)

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Marp renderer not found: {str(e)}. Please install with: npm install -g @marp-team/marp-cli"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate presentation: {str(e)}"
        )


@router.post("/save-original/{task_id}")
async def save_original_version(task_id: str):
    """
    Save original version of PPT when entering editor.

    This endpoint:
    1. Loads the latest markdown from workflow state
    2. Restores image tokens
    3. Saves markdown to intermediate directory (for correct image paths)
    4. Renders PPT to output directory as original.pptx

    Args:
        task_id: Task ID from the workflow

    Returns:
        Success message with output path

    Raises:
        HTTPException: If task not found or rendering fails
    """
    from pathlib import Path
    from app.storage.checkpointer import get_checkpointer
    from app.services.renderer.marp_engine import MarpEngine
    from app.services.parser.image_manager import ImageManager

    # Load workflow state
    checkpointer = get_checkpointer()
    state = checkpointer.load_state(task_id)

    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    # Get the latest markdown content
    marp_markdown = state.get("marp_markdown", "")
    if not marp_markdown:
        raise HTTPException(
            status_code=404,
            detail=f"No markdown content found for task: {task_id}"
        )

    # Get output format and token map
    output_format = state.get("output_format", "pptx")
    image_token_map = state.get("image_token_map", {})

    try:
        # Restore tokens if token map exists
        if image_token_map:
            image_manager = ImageManager(Path("data/workflow/intermediate"))
            marp_markdown = image_manager.restore_tokens_to_markdown_enhanced(
                tokenized_content=marp_markdown,
                token_map=image_token_map,
                output_format='marp'
            )

        # Save markdown to intermediate directory (for correct image paths)
        intermediate_dir = Path("data/workflow/intermediate") / task_id
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        input_md = intermediate_dir / "original.md"
        input_md.write_text(marp_markdown, encoding='utf-8')

        # Render to output directory
        output_dir = Path("data/workflow/output") / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_base = output_dir / "original"

        # Render markdown to presentation format
        engine = MarpEngine()
        success = engine.render(
            input_md=input_md,
            output_path=output_base,
            format=output_format,
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to render original presentation"
            )

        output_path = output_base.with_suffix(f".{output_format}")
        return {
            "status": "success",
            "message": "Original version saved",
            "output_path": str(output_path),
            "markdown_path": str(input_md)
        }

    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Marp renderer not found: {str(e)}. Please install with: npm install -g @marp-team/marp-cli"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save original version: {str(e)}"
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
