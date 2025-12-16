"""Checkpointer implementation for workflow state persistence.

This module provides persistent workflow state management using SQLite,
replacing the in-memory MemorySaver for reliable state persistence across
server restarts and supporting long-running workflows.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    SQLITE_AVAILABLE = False

from app.graph.state import TaskStatus, WorkflowState


class WorkflowCheckpointer:
    """Workflow state persistence manager with SQLite backend.

    This class provides a high-level interface for saving and loading
    workflow states, using SqliteSaver for LangGraph + JSON files for quick access.

    When SQLite is not available, falls back to MemorySaver for backward compatibility.
    """

    def __init__(
        self,
        db_path: str = "data/workflows/checkpoints.db",
        json_path: str = "data/workflows/workflow_state.db",
    ):
        """Initialize the checkpointer.

        Args:
            db_path: Path for SQLite database (LangGraph checkpointer)
            json_path: Path for JSON file storage (fallback/quick access)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.json_path = Path(json_path)
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize appropriate saver
        if not SQLITE_AVAILABLE:
            raise ImportError(
                "langgraph-checkpoint-sqlite is not installed. "
                "Please install it with: uv add langgraph-checkpoint-sqlite"
            )

        # Use from_conn_string with file path (not URI format)
        # from_conn_string expects a plain file path string
        self._saver_cm = SqliteSaver.from_conn_string(str(self.db_path))
        self._saver = self._saver_cm.__enter__()
        self._use_sqlite = True
        print(f"💾 Using SQLite checkpointer for persistent storage at {self.db_path.absolute()}")

    @property
    def saver(self):
        """Get the underlying saver for LangGraph integration.

        Returns:
            SqliteSaver if SQLite available, MemorySaver otherwise
        """
        return self._saver

    def close(self) -> None:
        """Close the checkpointer and cleanup resources."""
        if self._saver_cm is not None:
            try:
                self._saver_cm.__exit__(None, None, None)
                print("🔒 SQLite connection closed")
            except Exception as e:
                print(f"⚠️  Error closing SQLite connection: {e}")

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
        tasks_dir = self.json_path.parent / "tasks"

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
        task_file = self.json_path.parent / "tasks" / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
            return True
        return False

    def _save_to_json(self, task_id: str, state: WorkflowState) -> None:
        """Save state to JSON file for quick access."""
        tasks_dir = self.json_path.parent / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        task_file = tasks_dir / f"{task_id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(dict(state), f, ensure_ascii=False, indent=2)

    def _load_from_json(self, task_id: str) -> Optional[WorkflowState]:
        """Load state from JSON file."""
        task_file = self.json_path.parent / "tasks" / f"{task_id}.json"

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


def get_checkpointer(
    db_path: str | None = None,
    json_path: str | None = None,
) -> WorkflowCheckpointer:
    """Get or create global checkpointer instance with SQLite configuration.

    Args:
        db_path: Path for SQLite database (overrides default)
        json_path: Path for JSON file storage (overrides default)

    Returns:
        WorkflowCheckpointer instance
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = WorkflowCheckpointer(
            db_path=db_path or "data/workflows/checkpoints.db",
            json_path=json_path or "data/workflows/workflow_state.db",
        )
    return _checkpointer