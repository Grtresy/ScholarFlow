#!/usr/bin/env python3
"""
LangGraph Server Wrapper for Node.js

This script provides a bridge between Node.js LangGraph CLI and
the Python LangGraph workflow implementation.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.pregel import serve_graph
from app.graph.workflow import get_workflow
from app.storage.checkpointer import get_checkpointer

def main():
    """Start the LangGraph server."""
    workflow = get_workflow()
    checkpointer = get_checkpointer()

    print("🚀 Starting LangGraph Server...")
    print(f"📦 Workflow: {workflow}")
    print(f"💾 Checkpointer: {checkpointer}")

    serve_graph(
        graph=workflow,
        host="0.0.0.0",
        port=8123,
    )

if __name__ == "__main__":
    main()
