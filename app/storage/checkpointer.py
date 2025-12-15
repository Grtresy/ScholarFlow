"""Checkpointer implementation for workflow state persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import TaskStatus, WorkflowState


class WorkflowCheckpointer:
    """Workflow state persistence manager.

    This class provides a high-level interface for saving and loading
    workflow states, using MemorySaver for LangGraph + JSON files for persistence.
    """

    def __init__(self, db_path: str = "data/workflows/workflow_state.db"):
        """Initialize the checkpointer.

        Args:
            db_path: Path for storage (used for JSON files)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize memory saver for LangGraph
        self._saver = MemorySaver()

    @property
    def saver(self) -> MemorySaver:
        """Get the underlying MemorySaver for LangGraph integration."""
        return self._saver

    def save_state(
        self,
        task_id: str,
        state: WorkflowState,
        node_name: str,
    ) -> None:
        """Save workflow state as a checkpoint.

        Args:
            task_id: Task identifier
            state: Current workflow state
            node_name: Name of the current node
        """
        # Update timestamp
        state["updated_at"] = datetime.now().isoformat()

        # Add to execution log
        log_entry = {
            "timestamp": state["updated_at"],
            "node": node_name,
            "status": state.get("status", TaskStatus.PENDING.value),
            "progress": state.get("progress_percentage", 0.0),
        }

        if "execution_log" not in state:
            state["execution_log"] = []
        state["execution_log"].append(log_entry)

        # Save to custom storage for quick access
        self._save_to_json(task_id, state)

    def load_state(self, task_id: str) -> Optional[WorkflowState]:
        """Load workflow state by task ID.

        Args:
            task_id: Task identifier

        Returns:
            Workflow state if found, None otherwise
        """
        return self._load_from_json(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List all tasks with optional status filter.

        Args:
            status: Filter by task status
            limit: Maximum number of tasks to return

        Returns:
            List of task summaries
        """
        tasks = []
        tasks_dir = self.db_path.parent / "tasks"

        if not tasks_dir.exists():
            return []

        for task_file in tasks_dir.glob("*.json"):
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    state = json.load(f)

                if status and state.get("status") != status.value:
                    continue

                tasks.append(
                    {
                        "task_id": state.get("task_id"),
                        "status": state.get("status"),
                        "progress": state.get("progress_percentage", 0),
                        "current_step": state.get("current_step", ""),
                        "created_at": state.get("created_at"),
                        "updated_at": state.get("updated_at"),
                        "needs_review": state.get("needs_human_review", False),
                    }
                )
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by updated_at descending
        tasks.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """Delete a task's state.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted, False if not found
        """
        task_file = self.db_path.parent / "tasks" / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
            return True
        return False

    def _save_to_json(self, task_id: str, state: WorkflowState) -> None:
        """Save state to JSON file for quick access."""
        tasks_dir = self.db_path.parent / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / f"{task_id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(dict(state), f, ensure_ascii=False, indent=2)

    def _load_from_json(self, task_id: str) -> Optional[WorkflowState]:
        """Load state from JSON file."""
        task_file = self.db_path.parent / "tasks" / f"{task_id}.json"

        if not task_file.exists():
            return None

        try:
            with open(task_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return WorkflowState(**data)
        except (json.JSONDecodeError, TypeError):
            return None


# Global checkpointer instance
_checkpointer: Optional[WorkflowCheckpointer] = None


def get_checkpointer() -> WorkflowCheckpointer:
    """Get or create global checkpointer instance."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = WorkflowCheckpointer()
    return _checkpointer
