"""Text splitting node for workflow."""

from datetime import datetime
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState
from app.services.llm.split import merge_chunks, split_markdown


def node_split_markdown(state: WorkflowState) -> Dict[str, Any]:
    """Split markdown text into chunks.

    This node:
    - Splits markdown by sections and headers
    - Applies max_chars limit
    - Merges to target chunk count

    Args:
        state: Current workflow state

    Returns:
        State updates with chunks and chunks_count
    """
    # Use tokenized_text to preserve image tokens during splitting
    markdown_text = state.get("tokenized_text", state.get("markdown_text", ""))
    max_chars = state.get("max_chars", 8000)
    target_chunks = state.get("target_chunks", 3)

    if not markdown_text:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "No markdown text to split",
            "current_step": "分块失败：没有Markdown文本",
        }

    try:
        # Split markdown into chunks
        chunks = split_markdown(markdown_text, max_chars=max_chars)

        # Merge to target count if specified
        if target_chunks and target_chunks > 0:
            chunks = merge_chunks(chunks, target_count=target_chunks)

        # Ensure chunks have proper structure
        formatted_chunks = []
        for chunk in chunks:
            formatted_chunks.append({
                "id": chunk.get("id", len(formatted_chunks) + 1),
                "title": chunk.get("title", f"Chunk {len(formatted_chunks) + 1}"),
                "text": chunk.get("text", ""),
            })

        # Log success
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "text_splitting",
            "message": f"Text split into {len(formatted_chunks)} chunks",
            "chunk_count": len(formatted_chunks),
        }

        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)

        return {
            "status": TaskStatus.STAGE1_PROCESSING.value,
            "chunks": formatted_chunks,
            "chunks_count": len(formatted_chunks),
            "current_chunk_index": 0,
            "stage1_results": [],
            "stage1_completed": 0,
            "current_step": f"分块完成，共 {len(formatted_chunks)} 个chunk",
            "progress_percentage": 20.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }

    except Exception as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"Text splitting failed: {e}",
            "current_step": f"分块失败：{e}",
        }
