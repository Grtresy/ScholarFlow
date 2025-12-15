"""State schema definition for LangGraph workflow."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from typing_extensions import TypedDict


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    PARSING = "parsing"
    SPLITTING = "splitting"
    STAGE1_PROCESSING = "stage1_processing"
    MERGING = "merging"
    HUMAN_REVIEW = "human_review"
    STAGE2_PROCESSING = "stage2_processing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class PresentationStyle(str, Enum):
    """Presentation style enumeration."""

    ACADEMIC = "academic"
    POPULAR = "popular"
    BUSINESS = "business"


class ChunkData(TypedDict):
    """Data structure for a text chunk."""

    id: int
    title: str
    text: str
    start_line: Optional[int]
    end_line: Optional[int]


class Stage1Result(TypedDict):
    """Data structure for Stage 1 processing result."""

    chunk_id: int
    chunk_title: str
    outline: str
    success: bool
    error: Optional[str]


class ReviewPoint(TypedDict):
    """Data structure for a review point."""

    type: str
    node: str
    content: str
    prompt: Optional[str]
    timestamp: str


class WorkflowState(TypedDict, total=False):
    """Complete workflow state schema for LangGraph.

    This TypedDict defines all state fields that flow through the workflow.
    Using total=False allows optional fields.
    """

    # ===== Task basic info =====
    task_id: str
    status: str  # TaskStatus value
    created_at: str  # ISO format datetime
    updated_at: str  # ISO format datetime

    # ===== Input parameters =====
    pdf_path: str
    presentation_style: str  # PresentationStyle value
    max_chars: int
    target_chunks: int
    output_format: str  # pptx/pdf/html

    # ===== Stage 1: PDF parsing =====
    markdown_text: str
    markdown_path: str
    image_paths: List[str]
    parse_metadata: Dict[str, Any]

    # ===== Stage 2: Text splitting =====
    chunks: List[ChunkData]
    chunks_count: int

    # ===== Stage 3: Stage 1 processing =====
    current_chunk_index: int
    stage1_results: List[Stage1Result]
    stage1_completed: int
    stage1_failed: List[int]

    # ===== Stage 4: Outline merging =====
    merged_outline: str
    merged_outline_path: str

    # ===== Stage 5: Stage 2 processing =====
    marp_markdown: str
    marp_markdown_path: str

    # ===== Stage 6: Rendering =====
    output_path: str

    # ===== Human-in-the-loop =====
    needs_human_review: bool
    review_points: List[ReviewPoint]
    human_feedback: Dict[str, Any]
    approved: bool

    # ===== Error handling =====
    error_message: str
    error_details: Dict[str, Any]
    retry_count: int
    max_retries: int

    # ===== Progress tracking =====
    progress_percentage: float
    current_step: str
    step_details: Dict[str, Any]

    # ===== Execution log =====
    execution_log: List[Dict[str, Any]]


def create_initial_state(
    task_id: str,
    pdf_path: str,
    presentation_style: str = PresentationStyle.ACADEMIC.value,
    max_chars: int = 6000,
    target_chunks: int = 6,
    output_format: str = "pptx",
    enable_human_review: bool = True,
    max_retries: int = 3,
) -> WorkflowState:
    """Create initial workflow state.

    Args:
        task_id: Unique task identifier
        pdf_path: Path to the PDF file
        presentation_style: Style of presentation (academic/popular/business)
        max_chars: Maximum characters per chunk
        target_chunks: Target number of chunks
        output_format: Output format (pptx/pdf/html)
        enable_human_review: Whether to enable human review
        max_retries: Maximum retry attempts

    Returns:
        Initial workflow state
    """
    now = datetime.now().isoformat()

    return WorkflowState(
        # Task basic info
        task_id=task_id,
        status=TaskStatus.PENDING.value,
        created_at=now,
        updated_at=now,
        # Input parameters
        pdf_path=pdf_path,
        presentation_style=presentation_style,
        max_chars=max_chars,
        target_chunks=target_chunks,
        output_format=output_format,
        # Stage 1: PDF parsing
        markdown_text="",
        markdown_path="",
        image_paths=[],
        parse_metadata={},
        # Stage 2: Text splitting
        chunks=[],
        chunks_count=0,
        # Stage 3: Stage 1 processing
        current_chunk_index=0,
        stage1_results=[],
        stage1_completed=0,
        stage1_failed=[],
        # Stage 4: Outline merging
        merged_outline="",
        merged_outline_path="",
        # Stage 5: Stage 2 processing
        marp_markdown="",
        marp_markdown_path="",
        # Stage 6: Rendering
        output_path="",
        # Human-in-the-loop
        needs_human_review=enable_human_review,
        review_points=[],
        human_feedback={},
        approved=False,
        # Error handling
        error_message="",
        error_details={},
        retry_count=0,
        max_retries=max_retries,
        # Progress tracking
        progress_percentage=0.0,
        current_step="任务已创建",
        step_details={},
        # Execution log
        execution_log=[],
    )
