"""Stage 1 processing node for workflow (async version)."""

from datetime import datetime
from typing import Any, Dict, Literal

from app.graph.state import TaskStatus, WorkflowState
from app.services.llm.provider import LLMClient
from app.services.llm.prompts.prompt_templates import STAGE1_PROMPT


async def node_stage1_process(state: WorkflowState) -> Dict[str, Any]:
    """Process a single chunk with Stage 1 LLM call (async).

    This node:
    - Gets the current chunk to process
    - Calls LLM with Stage 1 prompt asynchronously
    - Records the result
    - Advances to next chunk or completes

    Args:
        state: Current workflow state

    Returns:
        State updates with stage1_results updated
    """
    chunks = state.get("chunks", [])
    current_index = state.get("current_chunk_index", 0)
    stage1_results = state.get("stage1_results", [])
    style = state.get("presentation_style", "academic")

    # Check if all chunks processed
    if current_index >= len(chunks):
        return {
            "status": TaskStatus.MERGING.value,
            "stage1_completed": len(chunks),
            "current_step": f"Stage 1 完成，共处理 {len(chunks)} 个chunk",
            "progress_percentage": 50.0,
            "updated_at": datetime.now().isoformat(),
        }

    chunk = chunks[current_index]
    chunk_id = chunk.get("id", current_index + 1)
    chunk_title = chunk.get("title", f"Chunk {chunk_id}")
    chunk_text = chunk.get("text", "")

    try:
        # Format prompt with style and content
        prompt = STAGE1_PROMPT.format(style=style.capitalize(), content=chunk_text)

        # Call LLM asynchronously
        client = LLMClient()
        response = await client.acomplete(
            prompt=prompt,
            max_tokens=4000,
            temperature=0.7,
        )

        outline = response.get("content", "")

        # Record successful result
        result = {
            "chunk_id": chunk_id,
            "chunk_title": chunk_title,
            "outline": outline,
            "success": True,
            "error": None,
        }
        stage1_results.append(result)

        # Log success
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "stage1_chunk_processed",
            "chunk_id": chunk_id,
            "chunk_title": chunk_title,
            "outline_length": len(outline),
        }
        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)

        # Calculate progress (20% + 30% for stage1)
        progress = 20.0 + (30.0 * (current_index + 1) / len(chunks))

        return {
            "current_chunk_index": current_index + 1,
            "stage1_results": stage1_results,
            "stage1_completed": current_index + 1,
            "current_step": f"Stage 1: 处理chunk {current_index + 1}/{len(chunks)}",
            "progress_percentage": progress,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }

    except Exception as e:
        # Record failed result
        result = {
            "chunk_id": chunk_id,
            "chunk_title": chunk_title,
            "outline": "",
            "success": False,
            "error": str(e),
        }
        stage1_results.append(result)

        # Track failed chunks
        stage1_failed = state.get("stage1_failed", [])
        stage1_failed.append(chunk_id)

        # Log failure
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "stage1_chunk_failed",
            "chunk_id": chunk_id,
            "error": str(e),
        }
        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)

        # Continue to next chunk despite failure
        return {
            "current_chunk_index": current_index + 1,
            "stage1_results": stage1_results,
            "stage1_completed": current_index + 1,
            "stage1_failed": stage1_failed,
            "current_step": f"Stage 1: chunk {chunk_id} 失败，继续处理",
            "progress_percentage": 20.0 + (30.0 * (current_index + 1) / len(chunks)),
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }


def should_continue_stage1(state: WorkflowState) -> Literal["continue", "merge"]:
    """Determine if Stage 1 should continue or proceed to merge.

    Args:
        state: Current workflow state

    Returns:
        'continue' to process next chunk, 'merge' to proceed to outline merging
    """
    chunks = state.get("chunks", [])
    current_index = state.get("current_chunk_index", 0)

    if current_index < len(chunks):
        return "continue"
    else:
        return "merge"
