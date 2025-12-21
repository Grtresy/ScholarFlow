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
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    SQLITE_AVAILABLE = True

    # Monkey patch for aiosqlite.Connection to add is_alive() method
    # This is needed for compatibility with langgraph-checkpoint-sqlite 3.0.1
    if not hasattr(aiosqlite.Connection, 'is_alive'):
        def _is_alive(self) -> bool:
            """Check if the connection is alive."""
            return self._conn is not None
        aiosqlite.Connection.is_alive = _is_alive

except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    SQLITE_AVAILABLE = False

from app.graph.state import TaskStatus, WorkflowState


class WorkflowCheckpointer:
    """Workflow state persistence manager with SQLite backend.

    This class provides a high-level interface for saving and loading
    workflow states, using AsyncSqliteSaver for LangGraph + JSON files for quick access.

    When SQLite is not available, falls back to MemorySaver for backward compatibility.

    NOTE: AsyncSqliteSaver requires async initialization.
    Call await checkpointer.initialize() after creating the instance.
    """

    def __init__(
        self,
        db_path: str = "data/workflow/checkpoints.db",
        json_path: str = "data/workflow/workflow_state.db",
    ):
        """Initialize the checkpointer (without opening connection).

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

        # Create the async context manager
        self._saver_cm = None
        self._saver = None
        self._initialized = False
        self._use_sqlite = True
        print(f"💾 AsyncSqliteSaver ready for {self.db_path.absolute()}")

    async def initialize(self) -> None:
        """Initialize the async checkpointer using async with pattern.

        Should be called once at startup:
            checkpointer = get_checkpointer()
            await checkpointer.initialize()
        """
        if not self._initialized:
            # Use standard async with pattern from LangGraph docs
            self._saver_cm = AsyncSqliteSaver.from_conn_string(str(self.db_path))
            self._saver = await self._saver_cm.__aenter__()
            self._initialized = True
            print(f"✓ SQLite connection established")

    @property
    def saver(self):
        """Get the underlying saver for LangGraph integration.

        Returns:
            AsyncSqliteSaver if SQLite available, MemorySaver otherwise

        Raises:
            RuntimeError if not initialized yet
        """
        if not self._initialized:
            raise RuntimeError(
                "Checkpointer not initialized. Call await checkpointer.initialize() first."
            )
        return self._saver

    async def close(self) -> None:
        """Close the checkpointer and cleanup resources."""
        if self._saver_cm is not None and self._initialized:
            try:
                await self._saver_cm.__aexit__(None, None, None)
                self._initialized = False
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

        # Trigger WebSocket notification (non-blocking)
        try:
            import asyncio
            from app.api.websocket import send_status_update

            # Create a new event loop for the callback if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an async context, schedule the task
                    asyncio.create_task(
                        send_status_update(
                            task_id=task_id,
                            status=TaskStatus(state.get("status", TaskStatus.PENDING.value)),
                            progress=state.get("progress_percentage", 0.0),
                            current_step=state.get("current_step", ""),
                            updated_fields=["status", "progress_percentage", "current_step"]
                        )
                    )
                else:
                    # If no event loop is running, we can't send the notification
                    pass
            except RuntimeError:
                # No event loop exists
                pass
        except Exception as e:
            # Silently ignore WebSocket errors to avoid breaking the main workflow
            print(f"⚠️  WebSocket notification error: {e}")

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
        # Save to the task's intermediate directory for better organization
        task_dir = self.json_path.parent / "intermediate" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        task_file = task_dir / f"{task_id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(dict(state), f, ensure_ascii=False, indent=2)

    def _load_from_json(self, task_id: str) -> Optional[WorkflowState]:
        """Load state from JSON file."""
        # Load from the task's intermediate directory
        task_file = self.json_path.parent / "intermediate" / task_id / f"{task_id}.json"

        if not task_file.exists():
            return None

        try:
            with open(task_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return WorkflowState(**data)
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error in {task_file}: {e}")
            return None
        except TypeError as e:
            print(f"❌ Type error in {task_file}: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error loading {task_file}: {e}")
            return None


# Global checkpointer instance
_checkpointer: Optional[WorkflowCheckpointer] = None


async def initialize_checkpointer(
    db_path: str | None = None,
    json_path: str | None = None,
) -> WorkflowCheckpointer:
    """Initialize and return the global checkpointer instance.

    Call this once at application startup:
        checkpointer = await initialize_checkpointer()

    Args:
        db_path: Path for SQLite database (overrides default)
        json_path: Path for JSON file storage (overrides default)

    Returns:
        Initialized WorkflowCheckpointer instance
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = WorkflowCheckpointer(
            db_path=db_path or "data/workflow/checkpoints.db",
            json_path=json_path or "data/workflow/workflow_state.db",
        )
        await _checkpointer.initialize()
    return _checkpointer


def get_checkpointer(
    db_path: str | None = None,
    json_path: str | None = None,
) -> WorkflowCheckpointer:
    """Get or create global checkpointer instance (without async initialization).

    IMPORTANT: If checkpointer doesn't exist yet, it will be created but NOT initialized.
    You must call await checkpointer.initialize() before using it.

    For automatic initialization, use await initialize_checkpointer() instead.

    Args:
        db_path: Path for SQLite database (overrides default)
        json_path: Path for JSON file storage (overrides default)

    Returns:
        WorkflowCheckpointer instance (may not be initialized yet)
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = WorkflowCheckpointer(
            db_path=db_path or "data/workflow/checkpoints.db",
            json_path=json_path or "data/workflow/workflow_state.db",
        )
    return _checkpointer