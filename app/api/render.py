"""Rendering API routes for live preview."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.parser.image_manager import ImageManager
from app.services.renderer.marp_engine import MarpEngine

router = APIRouter(prefix="/api/render", tags=["render"])


class RenderPreviewRequest(BaseModel):
    """Request model for rendering preview."""
    markdown: str = ...
    task_id: Optional[str] = None
    base_url: Optional[str] = None


class RenderPreviewResponse(BaseModel):
    """Response model for render preview."""
    html: str


def _validate_task_id(task_id: str) -> bool:
    """Validate task_id format for security.

    Args:
        task_id: Task ID to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9_-]{3,50}$'
    return bool(re.match(pattern, task_id))


def _inject_base_href(html: str, task_id: str) -> str:
    """Inject base href tag into HTML for image API routing.

    Args:
        html: HTML content to modify
        task_id: Task ID for image URL generation

    Returns:
        Modified HTML with base tag injected
    """
    base_url = f"/api/images/{task_id}/"
    base_tag = f'<base href="{base_url}">'

    if '<head>' in html:
        # Inject into head tag
        return html.replace('<head>', f'<head>\n    {base_tag}')
    elif '<!DOCTYPE' in html or '<html' in html:
        # If no head tag, inject after opening html tag
        if '<html>' in html:
            return html.replace('<html>', f'<html>\n<head>\n    {base_tag}\n</head>')
        elif '<html ' in html:
            # Extract attributes from opening html tag
            html_start = html.index('<html')
            html_end = html.index('>', html_start) + 1
            opening_tag = html[html_start:html_end]
            rest = html[html_end:]
            return f'{opening_tag}\n<head>\n    {base_tag}\n</head>{rest}'

    # Fallback: prepend to body or return as is
    if '<body>' in html:
        return html.replace('<body>', f'<head>\n    {base_tag}\n</head>\n<body>')

    return html



@router.post("/preview", response_model=RenderPreviewResponse)
async def render_preview(request: RenderPreviewRequest):
    """Render markdown to HTML for preview using MarpEngine.

    Args:
        request: RenderPreviewRequest containing markdown content and optional task_id

    Returns:
        RenderPreviewResponse with HTML content
    """
    try:
        # Validate task_id if provided
        if request.task_id:
            if not _validate_task_id(request.task_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid task_id format: {request.task_id}"
                )

        # Initialize MarpEngine with project root
        project_root = Path(__file__).resolve().parent.parent.parent
        engine = MarpEngine(project_root=project_root)

        # Process markdown content
        markdown_content = request.markdown

        # If task_id is provided, restore tokens and save to task directory
        if request.task_id:
            try:
                # Load token map
                token_map_path = project_root / "data" / "workflow" / "intermediate" / request.task_id / "token_map.json"
                if token_map_path.exists():
                    with open(token_map_path, 'r', encoding='utf-8') as f:
                        token_map = json.load(f)

                    # Determine base URL for image links
                    # Use provided base_url, or default to localhost:8000
                    base_url = request.base_url or "http://localhost:8000"
                    # Remove trailing slash if present
                    base_url = base_url.rstrip('/')

                    # Restore tokens using ImageManager
                    image_manager = ImageManager(project_root / "data" / "workflow" / "intermediate")
                    markdown_content = image_manager.restore_tokens_to_markdown_enhanced(
                        tokenized_content=request.markdown,
                        token_map=token_map,
                        output_format='marp',
                        task_id=request.task_id,
                        base_url=base_url
                    )

                    # Save to presentation.md in task directory
                    task_dir = project_root / "data" / "workflow" / "intermediate" / request.task_id
                    presentation_path = task_dir / "presentation.md"
                    task_dir.mkdir(parents=True, exist_ok=True)
                    with open(presentation_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                else:
                    # Token map not found, log warning but continue
                    print(f"Warning: Token map not found at {token_map_path}")
            except Exception as e:
                # Log error but continue with original markdown
                print(f"Error restoring tokens: {str(e)}")
                pass

        # Create temporary directory for rendering
        with tempfile.TemporaryDirectory() as temp_dir:
            # Render markdown to HTML using Marp
            output_path = await engine.render_markdown(
                markdown_content=markdown_content,
                output_dir=temp_dir,
                format="html",
                allow_local_files=True
            )

            # Read the generated HTML file
            with open(output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Inject base href if task_id is provided
            if request.task_id:
                html_content = _inject_base_href(html_content, request.task_id)

            return RenderPreviewResponse(html=html_content)

    except HTTPException:
        raise
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


