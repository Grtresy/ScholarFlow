"""Initialization node for workflow."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.graph.state import TaskStatus, WorkflowState


def node_initialize(state: WorkflowState) -> Dict[str, Any]:
    """Initialize and validate task input.

    This node:
    - Validates the PDF path exists
    - Sets initial status
    - Records start time

    Args:
        state: Current workflow state

    Returns:
        State updates
    """
    pdf_path = state.get("pdf_path", "")

    # Validate PDF path
    if not pdf_path:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": "PDF path is required",
            "current_step": "初始化失败：缺少PDF路径",
        }

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"PDF file not found: {pdf_path}",
            "current_step": f"初始化失败：文件不存在 {pdf_path}",
        }

    if not pdf_file.suffix.lower() == ".pdf":
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"File is not a PDF: {pdf_path}",
            "current_step": "初始化失败：文件不是PDF格式",
        }

    # Log initialization
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "initialization",
        "message": f"Task initialized with PDF: {pdf_file.name}",
    }

    execution_log = state.get("execution_log", [])
    execution_log.append(log_entry)

    return {
        "status": TaskStatus.PARSING.value,
        "current_step": "初始化完成，开始解析PDF",
        "progress_percentage": 5.0,
        "updated_at": datetime.now().isoformat(),
        "execution_log": execution_log,
    }
