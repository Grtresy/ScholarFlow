"""Rendering API routes for live preview."""

import os
import tempfile
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/render", tags=["render"])


class RenderPreviewRequest(BaseModel):
    """Request model for rendering preview."""
    markdown: str = ...


class RenderPreviewResponse(BaseModel):
    """Response model for render preview."""
    html: str


@router.post("/preview", response_model=RenderPreviewResponse)
async def render_preview(request: RenderPreviewRequest):
    """Render markdown to HTML for preview.

    Args:
        request: RenderPreviewRequest containing markdown content

    Returns:
        RenderPreviewResponse with HTML content
    """
    try:
        # For now, return a simple HTML wrapper with the markdown
        # In a real implementation, this would use the Marp renderer

        # Simple HTML conversion for preview
        # This is a placeholder - you would integrate with the actual Marp renderer here
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Marp Preview</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px;
            background: #fff;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.25em; }}
        p {{ margin-bottom: 16px; }}
        ul, ol {{ margin-bottom: 16px; padding-left: 2em; }}
        li {{ margin-bottom: 4px; }}
        code {{
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 2px 4px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 85%;
        }}
        pre {{
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
            margin-bottom: 16px;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #dfe2e5;
            padding-left: 16px;
            color: #6a737d;
            margin: 0;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }}
        table th, table td {{
            border: 1px solid #dfe2e5;
            padding: 6px 13px;
        }}
        table th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        .marp-slide {{
            /* Marp slide styles would go here */
            /* This is a simplified version for preview */
        }}
    </style>
</head>
<body>
    <div class="marp-slide">
        {markdown_to_html_basic(request.markdown)}
    </div>
</body>
</html>
"""

        return RenderPreviewResponse(html=html_content)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render preview: {str(e)}"
        )


def markdown_to_html_basic(markdown: str) -> str:
    """Basic markdown to HTML converter for preview.

    This is a simplified converter for preview purposes.
    In production, you would use a proper markdown library or the Marp renderer.

    Args:
        markdown: Markdown content

    Returns:
        HTML content
    """
    html = markdown

    # Basic markdown to HTML conversions
    # Headers
    html = html.replace('\n### ', '\n<h3>').replace('\n## ', '\n<h2>').replace('\n# ', '\n<h1>')
    html = html.replace('\n#### ', '\n<h4>').replace('\n##### ', '\n<h5>').replace('\n###### ', '\n<h6>')

    # Close headers
    for i in range(6, 0, -1):
        html = html.replace('\n' + '#' * i + ' ', '\n<h' + str(i) + '>')
        html = html + '</h' + str(i) + '>' if html.endswith('#' * i) else html

    # Bold and italic
    html = html.replace('**', '<strong>').replace('**', '</strong>')
    html = html.replace('*', '<em>').replace('*', '</em>')

    # Code blocks (simple)
    lines = html.split('\n')
    in_code_block = False
    result = []

    for line in lines:
        if line.strip().startswith('```'):
            if in_code_block:
                result.append('</pre>')
                in_code_block = False
            else:
                result.append('<pre><code>')
                in_code_block = True
        else:
            result.append(line)

    html = '\n'.join(result)

    # Lists (simple)
    html = html.replace('\n- ', '\n<li>').replace('\n* ', '\n<li>')
    html = html.replace('<li>', '<ul><li>') + '</ul>'

    # Paragraphs
    paragraphs = html.split('\n\n')
    html = '</p>\n<p>'.join(paragraphs)
    html = '<p>' + html + '</p>'

    return html
