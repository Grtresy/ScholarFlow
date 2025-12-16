"""Checkpointer implementation for workflow state persistence.

This module provides persistent workflow state management using MariaDB/MySQL,
replacing the in-memory MemorySaver for reliable state persistence across
server restarts and supporting long-running workflows.
"""
from __future__ import annotations

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from langgraph.checkpoint.mysql import MySQLSaver
    import aiomysql
    MYSQL_AVAILABLE = True
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver
    MYSQL_AVAILABLE = False

from app.graph.state import TaskStatus, WorkflowState


class WorkflowCheckpointer:
    """Workflow state persistence manager with MariaDB backend.

    This class provides a high-level interface for saving and loading
    workflow states, using MySQLSaver for LangGraph + JSON files for quick access.

    When MariaDB is not available, falls back to MemorySaver for backward compatibility.
    """

    def __init__(
        self,
        db_path: str = "data/workflows/workflow_state.db",
        mariadb_host: str = "localhost",
        mariadb_port: int = 3306,
        mariadb_user: str = "scholarflow",
        mariadb_password: str = "",
        mariadb_db: str = "scholarflow_state",
    ):
        """Initialize the checkpointer.

        Args:
            db_path: Path for JSON file storage (fallback/quick access)
            mariadb_host: MariaDB host
            mariadb_port: MariaDB port
            mariadb_user: MariaDB user
            mariadb_password: MariaDB password
            mariadb_db: MariaDB database name
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.mariadb_config = {
            "host": mariadb_host,
            "port": mariadb_port,
            "user": mariadb_user,
            "password": mariadb_password,
            "db": mariadb_db,
        }

        # Initialize appropriate saver
        if MYSQL_AVAILABLE:
            self._saver = None
            self._mysql_pool = None
            self._use_mysql = True
            print("💾 Using MariaDB checkpointer for persistent storage")
        else:
            self._saver = MemorySaver()
            self._use_mysql = False
            print("⚠️  MariaDB not available, using in-memory checkpointer (data will be lost on restart)")

    async def initialize(self) -> None:
        """Initialize the checkpointer and create MariaDB connection pool."""
        if not self._use_mysql or self._saver is not None:
            return

        try:
            # Create connection pool
            self._mysql_pool = aiomysql.create_pool(
                host=self.mariadb_config["host"],
                port=self.mariadb_config["port"],
                user=self.mariadb_config["user"],
                password=self.mariadb_config["password"],
                db=self.mariadb_config["db"],
                minsize=5,
                maxsize=20,
                pool_recycle=3600,  # Recycle connections every hour
            )

            # Create MySQL saver
            self._saver = MySQLSaver(self._mysql_pool)
            print("✅ MariaDB checkpointer initialized successfully")

        except Exception as e:
            print(f"❌ Failed to initialize MariaDB checkpointer: {e}")
            print("   Falling back to in-memory checkpointer")
            self._use_mysql = False
            self._saver = MemorySaver()

    @property
    def saver(self):
        """Get the underlying saver for LangGraph integration.

        Returns:
            MySQLSaver if MariaDB available, MemorySaver otherwise
        """
        if self._use_mysql and self._saver is None:
            raise RuntimeError(
                "MariaDB checkpointer not initialized. Call await checkpointer.initialize() first."
            )
        return self._saver

    async def close(self) -> None:
        """Close the checkpointer and cleanup resources."""
        if self._mysql_pool is not None:
            self._mysql_pool.close()
            await self._mysql_pool.wait_closed()
            print("🔒 MariaDB connection pool closed")

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


def get_checkpointer(
    mariadb_host: str | None = None,
    mariadb_port: int | None = None,
    mariadb_user: str | None = None,
    mariadb_password: str | None = None,
    mariadb_db: str | None = None,
) -> WorkflowCheckpointer:
    """Get or create global checkpointer instance with MariaDB configuration.

    Args:
        mariadb_host: MariaDB host (overrides config)
        mariadb_port: MariaDB port (overrides config)
        mariadb_user: MariaDB user (overrides config)
        mariadb_password: MariaDB password (overrides config)
        mariadb_db: MariaDB database name (overrides config)

    Returns:
        WorkflowCheckpointer instance
    """
    global _checkpointer
    if _checkpointer is None:
        # Import here to avoid circular dependency
        from app.core.config import get_settings

        settings = get_settings()

        _checkpointer = WorkflowCheckpointer(
            db_path="data/workflows/workflow_state.db",
            mariadb_host=mariadb_host or settings.mariadb_host,
            mariadb_port=mariadb_port or settings.mariadb_port,
            mariadb_user=mariadb_user or settings.mariadb_user,
            mariadb_password=mariadb_password or settings.mariadb_password,
            mariadb_db=mariadb_db or settings.mariadb_db,
        )
    return _checkpointer
