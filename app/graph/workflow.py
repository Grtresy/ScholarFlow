"""Workflow compilation for ScholarFlow LangGraph."""

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.error_handling import node_handle_error
from app.graph.nodes.human_review import (
    node_human_review,
    node_process_feedback,
    route_after_feedback,
)
from app.graph.nodes.initialization import node_initialize
from app.graph.nodes.outline_merging import node_merge_outlines
from app.graph.nodes.pdf_parsing import node_parse_pdf
from app.graph.nodes.rendering import node_render
from app.graph.nodes.stage1_processing import node_stage1_process, should_continue_stage1
from app.graph.nodes.stage2_processing import node_stage2_process
from app.graph.nodes.text_splitting import node_split_markdown
from app.graph.state import TaskStatus, WorkflowState
from app.storage.checkpointer import get_checkpointer, initialize_checkpointer


def route_after_stage1(state: WorkflowState) -> str:
    """Route after Stage 1 processing."""
    return should_continue_stage1(state)


def route_after_merge(state: WorkflowState) -> str:
    """Route after outline merging.

    Args:
        state: Current workflow state

    Returns:
        'human_review' if review needed, 'stage2' otherwise
    """
    if state.get("status") == TaskStatus.HUMAN_REVIEW.value:
        return "human_review"
    elif state.get("status") == TaskStatus.STAGE2_PROCESSING.value:
        return "stage2"
    else:
        return "end"


def route_after_human_feedback(state: WorkflowState) -> str:
    """Route after human feedback processing."""
    return route_after_feedback(state)


def route_on_error(state: WorkflowState) -> str:
    """Route when error status is detected."""
    status = state.get("status", "")
    if status == TaskStatus.FAILED.value:
        return "handle_error"
    return "continue"


def route_after_error(state: WorkflowState) -> str:
    """Route after error handling based on updated status.

    Args:
        state: Current workflow state after error handling

    Returns:
        'retry' to restart from parsing, 'end' to finish
    """
    status = state.get("status", "")
    if status == TaskStatus.PARSING.value:
        # Successfully reset for retry - go back to parsing
        return "retry"
    elif status == TaskStatus.FAILED.value:
        # Max retries reached - end the workflow
        return "end"
    else:
        # Unexpected status - end the workflow
        return "end"


def create_workflow() -> StateGraph:
    """Create the ScholarFlow workflow graph.

    Returns:
        Compiled StateGraph workflow
    """
    # Create graph with state schema
    workflow = StateGraph(WorkflowState)

    # Add all nodes
    workflow.add_node("initialize", node_initialize)
    workflow.add_node("parse_pdf", node_parse_pdf)
    workflow.add_node("split_markdown", node_split_markdown)
    workflow.add_node("stage1_process", node_stage1_process)
    workflow.add_node("merge_outlines", node_merge_outlines)
    workflow.add_node("human_review", node_human_review)
    workflow.add_node("process_feedback", node_process_feedback)
    workflow.add_node("stage2_process", node_stage2_process)
    workflow.add_node("render", node_render)
    workflow.add_node("handle_error", node_handle_error)

    # Define edges
    # START -> initialize
    workflow.add_edge(START, "initialize")

    # initialize -> parse_pdf (or end on error)
    workflow.add_conditional_edges(
        "initialize",
        lambda s: "parse_pdf" if s.get("status") != TaskStatus.FAILED.value else "end",
        {"parse_pdf": "parse_pdf", "end": END},
    )

    # parse_pdf -> split_markdown (or end on error)
    workflow.add_conditional_edges(
        "parse_pdf",
        lambda s: "split_markdown" if s.get("status") != TaskStatus.FAILED.value else "handle_error",
        {"split_markdown": "split_markdown", "handle_error": "handle_error"},
    )

    # split_markdown -> stage1_process (or end on error)
    workflow.add_conditional_edges(
        "split_markdown",
        lambda s: "stage1_process" if s.get("status") != TaskStatus.FAILED.value else "handle_error",
        {"stage1_process": "stage1_process", "handle_error": "handle_error"},
    )

    # stage1_process -> (continue loop or merge)
    workflow.add_conditional_edges(
        "stage1_process",
        route_after_stage1,
        {"continue": "stage1_process", "merge": "merge_outlines"},
    )

    # merge_outlines -> human_review or stage2
    workflow.add_conditional_edges(
        "merge_outlines",
        route_after_merge,
        {"human_review": "human_review", "stage2": "stage2_process", "end": END},
    )

    # human_review -> process_feedback
    workflow.add_edge("human_review", "process_feedback")

    # process_feedback -> stage1 (regenerate), stage2 (approved), or end
    workflow.add_conditional_edges(
        "process_feedback",
        route_after_human_feedback,
        {"stage1": "stage1_process", "stage2": "stage2_process", "end": END},
    )

    # stage2_process -> render (or handle_error)
    workflow.add_conditional_edges(
        "stage2_process",
        lambda s: "render" if s.get("status") != TaskStatus.FAILED.value else "handle_error",
        {"render": "render", "handle_error": "handle_error"},
    )

    # render -> end
    workflow.add_edge("render", END)

    # handle_error -> (retry or end based on status)
    workflow.add_conditional_edges(
        "handle_error",
        route_after_error,
        {
            "retry": "parse_pdf",  # Retry: go back to parse_pdf
            "end": END,            # Fail: end the workflow
        }
    )

    return workflow


def compile_workflow(with_checkpointer: bool = True):
    """Compile the workflow with optional checkpointer.

    Args:
        with_checkpointer: Whether to include checkpointer for persistence

    Returns:
        Compiled workflow
    """
    workflow = create_workflow()

    if with_checkpointer:
        checkpointer = get_checkpointer()
        return workflow.compile(
            checkpointer=checkpointer.saver,
            interrupt_before=["process_feedback"]  # 在process_feedback节点前中断
        )
    else:
        return workflow.compile(interrupt_before=["process_feedback"])


def get_workflow():
    """Get or create compiled workflow instance.

    Returns:
        Compiled workflow
    """
    # Always recompile to ensure interrupt_before settings are applied
    # This is necessary because the global _compiled_workflow may be cached
    # from a previous version without interrupt_before
    return compile_workflow(with_checkpointer=True)


async def run_workflow(
    initial_state: WorkflowState,
    thread_id: str = None,
) -> Dict[str, Any]:
    """Run the workflow with initial state.

    Args:
        initial_state: Initial workflow state
        thread_id: Optional thread ID for persistence (defaults to task_id)

    Returns:
        Final workflow state
    """
    # Ensure checkpointer is initialized
    await initialize_checkpointer()

    workflow = get_workflow()
    thread_id = thread_id or initial_state.get("task_id", "default")

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # Run workflow
    final_state = await workflow.ainvoke(initial_state, config)
    # Save final state snapshot for later inspection/resume
    try:
        if final_state:
            checkpointer = get_checkpointer()
            task_id_to_save = thread_id or initial_state.get("task_id", "default")
            checkpointer.save_state(task_id_to_save, WorkflowState(**final_state), "end")
    except Exception:
        # Non-fatal if persistence fails
        pass
    return final_state


def run_workflow_sync(
    initial_state: WorkflowState,
    thread_id: str = None,
) -> Dict[str, Any]:
    """Run the workflow synchronously.

    Args:
        initial_state: Initial workflow state
        thread_id: Optional thread ID for persistence

    Returns:
        Final workflow state
    """
    workflow = get_workflow()
    thread_id = thread_id or initial_state.get("task_id", "default")

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # Run workflow
    final_state = workflow.invoke(initial_state, config)
    return final_state


async def resume_workflow(
    task_id: str,
    human_feedback: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Resume a paused workflow.

    Args:
        task_id: Task ID to resume
        human_feedback: Optional human feedback to inject

    Returns:
        Final workflow state
    """
    # Ensure checkpointer is initialized
    await initialize_checkpointer()

    workflow = get_workflow()

    config = {
        "configurable": {
            "thread_id": task_id,
        }
    }

    # 使用 update_state 注入 human_feedback 到 checkpoint state
    # 这是 LangGraph 推荐的方式，用于在 interrupt_before 后注入数据
    if human_feedback:
        await workflow.aupdate_state(
            config,
            {
                "human_feedback": human_feedback,
                "needs_human_review": False,
            }
        )

    # Resume workflow from interrupt point
    # 传入 None 告诉 LangGraph 从 checkpoint 继续，而不是重新开始
    final_state = await workflow.ainvoke(None, config)
    
    # Save final state to checkpointer (same as run_workflow)
    try:
        if final_state:
            checkpointer = get_checkpointer()
            checkpointer.save_state(task_id, WorkflowState(**final_state), "resume_end")
    except Exception:
        # Non-fatal if persistence fails
        pass
    
    return final_state

