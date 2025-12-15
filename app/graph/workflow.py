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
from app.storage.checkpointer import get_checkpointer


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

    # handle_error -> end (after retry logic)
    workflow.add_edge("handle_error", END)

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
        return workflow.compile(checkpointer=checkpointer.saver)
    else:
        return workflow.compile()


# Pre-compiled workflow instance
_compiled_workflow = None


def get_workflow():
    """Get or create compiled workflow instance.

    Returns:
        Compiled workflow
    """
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = compile_workflow(with_checkpointer=True)
    return _compiled_workflow


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
    workflow = get_workflow()
    thread_id = thread_id or initial_state.get("task_id", "default")

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # Run workflow
    final_state = await workflow.ainvoke(initial_state, config)
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
    workflow = get_workflow()
    checkpointer = get_checkpointer()

    # Load current state
    state = checkpointer.load_state(task_id)
    if not state:
        raise ValueError(f"No state found for task {task_id}")

    # Inject human feedback if provided
    if human_feedback:
        state["human_feedback"] = human_feedback
        state["needs_human_review"] = False

    config = {
        "configurable": {
            "thread_id": task_id,
        }
    }

    # Resume workflow
    final_state = await workflow.ainvoke(state, config)
    return final_state
