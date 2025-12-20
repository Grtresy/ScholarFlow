"""Rendering API routes for live preview."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.renderer.marp_engine import MarpEngine

router = APIRouter(prefix="/api/render", tags=["render"])


class RenderPreviewRequest(BaseModel):
    """Request model for rendering preview."""
    markdown: str = ...


class RenderPreviewResponse(BaseModel):
    """Response model for render preview."""
    html: str


@router.post("/preview", response_model=RenderPreviewResponse)
async def render_preview(request: RenderPreviewRequest):
    """Render markdown to HTML for preview using MarpEngine.

    Args:
        request: RenderPreviewRequest containing markdown content

    Returns:
        RenderPreviewResponse with HTML content
    """
    try:
        # Initialize MarpEngine with project root
        project_root = Path(__file__).resolve().parent.parent.parent
        engine = MarpEngine(project_root=project_root)

        # Create temporary directory for rendering
        with tempfile.TemporaryDirectory() as temp_dir:
            # Render markdown to HTML using Marp
            output_path = await engine.render_markdown(
                markdown_content=request.markdown,
                output_dir=temp_dir,
                format="html",
                allow_local_files=True
            )

            # Read the generated HTML file
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            return RenderPreviewResponse(html=html_content)

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Marp renderer not found: {str(e)}. Please install with: npm install -g @marp-team/marp-cli"
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Marp rendering failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render preview: {str(e)}"
        )

