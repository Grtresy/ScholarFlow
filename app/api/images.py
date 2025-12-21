"""Image serving API endpoints."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.services.parser.image_manager import ImageManager, create_image_manager
from app.core.config import get_settings

router = APIRouter(tags=["images"])

# Initialize image manager
settings = get_settings()
image_manager = create_image_manager(settings.data_dir or "data")


@router.get("/{task_id}/{filename}")
async def get_image(task_id: str, filename: str, request: Request):
    """Serve an image file for a specific task.

    Args:
        task_id: Task identifier
        filename: Image filename
        request: FastAPI request object

    Returns:
        Image file response
    """
    try:
        # Get image path
        task_info = image_manager.get_task_info(task_id)

        if not task_info["exists"]:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Check if image exists
        if filename not in task_info["images"]:
            raise HTTPException(status_code=404, detail=f"Image {filename} not found")

        # Get full path
        image_path = Path(task_info["path"]) / "images" / filename

        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found on disk")

        # Determine content type
        content_type = _get_content_type(image_path.suffix)

        # Return file with appropriate headers
        return FileResponse(
            path=image_path,
            media_type=content_type,
            filename=filename,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Access-Control-Allow-Origin": "*",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving image: {str(e)}")


@router.get("/{task_id}")
async def list_task_images(task_id: str):
    """List all images for a task.

    Args:
        task_id: Task identifier

    Returns:
        List of image information
    """
    try:
        task_info = image_manager.get_task_info(task_id)

        if not task_info["exists"]:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Build image list with URLs
        images = []
        for filename in task_info["images"]:
            image_url = f"/api/images/{task_id}/{filename}"
            images.append({
                "filename": filename,
                "url": image_url,
                "type": _get_content_type(Path(filename).suffix)
            })

        return {
            "task_id": task_id,
            "image_count": len(images),
            "images": images
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing images: {str(e)}")


@router.delete("/{task_id}")
async def delete_task_images(task_id: str):
    """Delete all images for a task.

    Args:
        task_id: Task identifier

    Returns:
        Deletion status
    """
    try:
        task_info = image_manager.get_task_info(task_id)

        if not task_info["exists"]:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        # Remove entire task directory
        task_dir = Path(task_info["path"])
        if task_dir.exists():
            import shutil
            shutil.rmtree(task_dir)

        return {
            "status": "success",
            "message": f"Task {task_id} and all images deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting task: {str(e)}")


def _get_content_type(extension: str) -> str:
    """Get MIME type for file extension.

    Args:
        extension: File extension (with or without dot)

    Returns:
        MIME type string
    """
    extension = extension.lower()

    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }

    return content_types.get(extension, "application/octet-stream")
