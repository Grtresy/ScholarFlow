"""Stage 2 processing node for workflow (async version)."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState
from app.services.llm.provider import LLMClient
from app.services.prompt_manager import get_prompt_manager


async def node_stage2_process(state: WorkflowState) -> Dict[str, Any]:
    """Process merged outline with Stage 2 LLM call (async).

    This node:
    - Takes the merged outline
    - Calls LLM with Stage 2 prompt to generate Marp Markdown asynchronously
    - Saves the result

    Args:
        state: Current workflow state

    Returns:
        State updates with marp_markdown
    """
    merged_outline = state.get("merged_outline", "")
    style = state.get("presentation_style", "academic")
    task_id = state.get("task_id", "unknown")

    if not merged_outline:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "No merged outline for Stage 2",
            "current_step": "Stage 2失败：没有合并后的大纲",
        }

    try:
        # Get prompt manager and format prompt
        prompt_manager = get_prompt_manager()
        prompt = prompt_manager.format_stage2_prompt(style=style, outline=merged_outline)

        # Call LLM asynchronously
        client = LLMClient()
        response = await client.acomplete(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.7,
        )

        marp_markdown = response.get("content", "")

        # Save Marp markdown
        output_dir = Path("data/intermediate") / task_id
        output_dir.mkdir(parents=True, exist_ok=True)
        marp_path = output_dir / "presentation.md"
        marp_path.write_text(marp_markdown, encoding="utf-8")

        # Log success
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "stage2_processed",
            "message": f"Generated Marp Markdown with {len(marp_markdown)} chars",
            "usage": response.get("usage", {}),
        }
        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)

        return {
            "status": TaskStatus.RENDERING.value,
            "marp_markdown": marp_markdown,
            "marp_markdown_path": str(marp_path),
            "current_step": "Stage 2完成，开始渲染",
            "progress_percentage": 80.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }

    except Exception as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"Stage 2 processing failed: {e}",
            "current_step": f"Stage 2失败：{e}",
        }
