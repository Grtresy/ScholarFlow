"""WebSocket implementation for real-time workflow updates."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.graph.state import TaskStatus, WorkflowState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


# ===== WebSocket Connection Manager =====

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        # task_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # connection -> task_id mapping
        self.connection_tasks: Dict[WebSocket, str] = {}

    async def connect(
        self,
        websocket: WebSocket,
        task_id: str
    ) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()

        self.active_connections[task_id].add(websocket)
        self.connection_tasks[websocket] = task_id

        logger.info(f"WebSocket connected for task {task_id}. "
                   f"Active connections: {len(self.active_connections[task_id])}")

    def disconnect(self, websocket: WebSocket) -> Optional[str]:
        """Remove a WebSocket connection."""
        task_id = self.connection_tasks.get(websocket)
        if task_id and task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)

            # Clean up empty task groups
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

            # Remove connection mapping
            del self.connection_tasks[websocket]

            if task_id:
                logger.info(f"WebSocket disconnected for task {task_id}. "
                           f"Remaining connections: {len(self.active_connections.get(task_id, []))}")

        return task_id

    async def send_personal_message(
        self,
        message: dict,
        task_id: str
    ) -> None:
        """Send a message to all connections for a specific task."""
        if task_id not in self.active_connections:
            return

        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = []

        for connection in list(self.active_connections[task_id]):
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = []

        for task_id in list(self.active_connections.keys()):
            for connection in list(self.active_connections[task_id]):
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting message: {e}")
                    disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def get_connection_count(self, task_id: str) -> int:
        """Get the number of active connections for a task."""
        return len(self.active_connections.get(task_id, []))


# Global connection manager instance
manager = ConnectionManager()


# ===== Message Models =====

class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""

    type: str
    data: dict
    timestamp: float

    class Config:
        use_enum_values = True


class AuthMessage(BaseModel):
    """Authentication message from client."""

    task_id: str
    token: Optional[str] = None


class StatusUpdateMessage(BaseModel):
    """Status update message."""

    task_id: str
    status: str
    progress: float
    current_step: str
    updated_fields: Optional[List[str]] = None


class ChunkProgressMessage(BaseModel):
    """Stage 1 chunk processing progress."""

    task_id: str
    chunk_index: int
    total_chunks: int
    completed_chunks: int
    current_chunk_content: Optional[str] = None


class RenderProgressMessage(BaseModel):
    """Rendering progress message."""

    task_id: str
    stage: str
    percentage: float
    output_format: str


class ReviewRequiredMessage(BaseModel):
    """Review required message."""

    task_id: str
    review_points: List[dict]
    can_edit: bool


class ErrorMessage(BaseModel):
    """Error message."""

    task_id: str
    error_code: str
    error_message: str
    node_name: Optional[str] = None
    recovery_hint: Optional[str] = None


class CompletedMessage(BaseModel):
    """Task completed message."""

    task_id: str
    result_url: Optional[str] = None
    output_format: str


# ===== Message Builders =====

def build_status_update(
    task_id: str,
    status: TaskStatus,
    progress: float,
    current_step: str,
    updated_fields: Optional[List[str]] = None
) -> dict:
    """Build a status update message."""
    return {
        "type": "status_update",
        "data": {
            "task_id": task_id,
            "status": status.value,
            "progress": progress,
            "current_step": current_step,
            "updated_fields": updated_fields or [],
        },
        "timestamp": datetime.now().timestamp()
    }


def build_chunk_progress(
    task_id: str,
    chunk_index: int,
    total_chunks: int,
    completed_chunks: int,
    current_chunk_content: Optional[str] = None
) -> dict:
    """Build a chunk progress message."""
    return {
        "type": "chunk_progress",
        "data": {
            "task_id": task_id,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks,
            "current_chunk_content": current_chunk_content,
        },
        "timestamp": datetime.now().timestamp()
    }


def build_render_progress(
    task_id: str,
    stage: str,
    percentage: float,
    output_format: str
) -> dict:
    """Build a render progress message."""
    return {
        "type": "render_progress",
        "data": {
            "task_id": task_id,
            "stage": stage,
            "percentage": percentage,
            "output_format": output_format,
        },
        "timestamp": datetime.now().timestamp()
    }


def build_review_required(
    task_id: str,
    review_points: List[dict],
    can_edit: bool = True
) -> dict:
    """Build a review required message."""
    return {
        "type": "review_required",
        "data": {
            "task_id": task_id,
            "review_points": review_points,
            "can_edit": can_edit,
        },
        "timestamp": datetime.now().timestamp()
    }


def build_error(
    task_id: str,
    error_code: str,
    error_message: str,
    node_name: Optional[str] = None,
    recovery_hint: Optional[str] = None
) -> dict:
    """Build an error message."""
    return {
        "type": "error",
        "data": {
            "task_id": task_id,
            "error_code": error_code,
            "error_message": error_message,
            "node_name": node_name,
            "recovery_hint": recovery_hint,
        },
        "timestamp": datetime.now().timestamp()
    }


def build_completed(
    task_id: str,
    result_url: Optional[str] = None,
    output_format: str = "pptx"
) -> dict:
    """Build a task completed message."""
    return {
        "type": "completed",
        "data": {
            "task_id": task_id,
            "result_url": result_url,
            "output_format": output_format,
        },
        "timestamp": datetime.now().timestamp()
    }


# ===== WebSocket Endpoints =====

@router.websocket("/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task updates."""
    await manager.connect(websocket, task_id)

    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            {
                "type": "connected",
                "data": {
                    "task_id": task_id,
                    "message": "WebSocket connection established",
                },
                "timestamp": datetime.now().timestamp()
            },
            task_id
        )

        # Keep the connection alive and handle incoming messages
        while True:
            # Wait for messages from client (for ping/pong, etc.)
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client messages if needed
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    {
                        "type": "pong",
                        "data": {"timestamp": datetime.now().timestamp()},
                        "timestamp": datetime.now().timestamp()
                    },
                    task_id
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ===== Public API for sending messages =====

async def send_status_update(
    task_id: str,
    status: TaskStatus,
    progress: float,
    current_step: str,
    updated_fields: Optional[List[str]] = None
) -> None:
    """Send a status update to connected clients."""
    message = build_status_update(task_id, status, progress, current_step, updated_fields)
    await manager.send_personal_message(message, task_id)


async def send_chunk_progress(
    task_id: str,
    chunk_index: int,
    total_chunks: int,
    completed_chunks: int,
    current_chunk_content: Optional[str] = None
) -> None:
    """Send chunk progress update."""
    message = build_chunk_progress(
        task_id, chunk_index, total_chunks, completed_chunks, current_chunk_content
    )
    await manager.send_personal_message(message, task_id)


async def send_render_progress(
    task_id: str,
    stage: str,
    percentage: float,
    output_format: str
) -> None:
    """Send rendering progress update."""
    message = build_render_progress(task_id, stage, percentage, output_format)
    await manager.send_personal_message(message, task_id)


async def send_review_required(
    task_id: str,
    review_points: List[dict],
    can_edit: bool = True
) -> None:
    """Send review required notification."""
    message = build_review_required(task_id, review_points, can_edit)
    await manager.send_personal_message(message, task_id)


async def send_error(
    task_id: str,
    error_code: str,
    error_message: str,
    node_name: Optional[str] = None,
    recovery_hint: Optional[str] = None
) -> None:
    """Send error notification."""
    message = build_error(task_id, error_code, error_message, node_name, recovery_hint)
    await manager.send_personal_message(message, task_id)


async def send_completed(
    task_id: str,
    result_url: Optional[str] = None,
    output_format: str = "pptx"
) -> None:
    """Send task completion notification."""
    message = build_completed(task_id, result_url, output_format)
    await manager.send_personal_message(message, task_id)


async def get_connection_count(task_id: str) -> int:
    """Get the number of active connections for a task."""
    return manager.get_connection_count(task_id)
