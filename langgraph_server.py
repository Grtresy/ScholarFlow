"""
LangGraph Server for ScholarFlow workflow.

This module deploys the ScholarFlow LangGraph workflow as a proper LangGraph server
that can be accessed by the LangGraph JS SDK from the React frontend.
"""

import argparse
import uvicorn
from langgraph_sdk.server import run_server
from app.graph.workflow import get_workflow
from app.storage.checkpointer import get_checkpointer


def run_langgraph_server():
    """Run the LangGraph server on the specified host and port."""
    workflow = get_workflow()
    checkpointer = get_checkpointer()

    run_server(
        workflows={"scholarflow": workflow},
        checkpointer=checkpointer,
        host="0.0.0.0",
        port=8123,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ScholarFlow LangGraph Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8123, help="Port to bind to")

    args = parser.parse_args()

    workflow = get_workflow()
    checkpointer = get_checkpointer()

    run_server(
        workflows={"scholarflow": workflow},
        checkpointer=checkpointer,
        host=args.host,
        port=args.port,
    )
