"""Stage 2 processing node for workflow (async version)."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState
from app.services.llm.provider import LLMClient
from app.services.llm.prompts.prompt_templates import format_stage2_prompt


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
    task_id = state.get("task_id")
    user_modifications = state.get("user_modifications", "")

    if not merged_outline:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "No merged outline for Stage 2",
            "current_step": "Stage 2失败：没有合并后的大纲",
        }

    try:
        # Format prompt with dynamic template system
        prompt = format_stage2_prompt(
            style=style,
            outline=merged_outline,
            task_id=task_id,
            user_modifications=user_modifications
        )

        # Call LLM asynchronously
        client = LLMClient()
        response = await client.acomplete(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.7,
            task_id=task_id,
            stage="stage2",
        )

        marp_markdown = response.get("content", "")

        # Save Marp markdown
        output_dir = Path("data/workflow/intermediate") / task_id
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
            "image_token_map": state.get("image_token_map"),  # 明确传递image_token_map
            "token_count": len(state.get("image_token_map", {})),
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
