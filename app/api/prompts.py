"""API routes for prompt template management."""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm.prompts.prompt_templates import (
    get_available_styles,
    _template_manager,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class TemplateResponse(BaseModel):
    """Response model for template data."""
    stage1: Dict[str, str]
    stage2: Dict[str, str]


@router.get("/templates", response_model=TemplateResponse)
async def get_templates():
    """Get all available prompt templates.

    Returns the Stage 1 and Stage 2 templates for all preset styles.
    """
    try:
        templates = _template_manager._preset_templates

        if not templates:
            # Fallback to embedded templates if no external templates found
            from app.services.llm.prompts.prompt_templates import _EMBEDDED_TEMPLATES
            templates = _EMBEDDED_TEMPLATES

        return TemplateResponse(
            stage1=templates.get("stage1", {}),
            stage2=templates.get("stage2", {}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load templates: {str(e)}")


@router.get("/templates/{style}/{stage}")
async def get_template(style: str, stage: str):
    """Get a specific template by style and stage.

    Args:
        style: Template style (academic, popular, business)
        stage: Template stage (stage1 or stage2)

    Returns:
        The template string
    """
    if stage not in ["stage1", "stage2"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage}. Use 'stage1' or 'stage2'",
        )

    try:
        template = _template_manager.get_template(task_id=None, stage=stage, style=style)

        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template not found for style '{style}' and stage '{stage}'",
            )

        return {"style": style, "stage": stage, "template": template}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.get("/styles")
async def get_available_styles_endpoint():
    """Get list of available preset styles.

    Returns a list of style names that have templates available.
    """
    try:
        styles = get_available_styles()
        return {"styles": styles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get styles: {str(e)}")
