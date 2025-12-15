#!/usr/bin/env python3
"""
Simplified LangGraph Server for Development

This script creates a simple server to expose the LangGraph workflow
for debugging and testing purposes.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.workflow import get_workflow
from app.storage.checkpointer import get_checkpointer

def main():
    """Display workflow information for debugging."""
    print("=" * 60)
    print("🔍 ScholarFlow LangGraph Workflow Debug Info")
    print("=" * 60)

    try:
        workflow = get_workflow()
        checkpointer = get_checkpointer()

        print(f"\n✅ Workflow loaded successfully!")
        print(f"📦 Workflow type: {type(workflow)}")
        print(f"💾 Checkpointer type: {type(checkpointer)}")

        print(f"\n📊 Workflow details:")
        print(f"   - Nodes: {list(workflow.nodes.keys()) if hasattr(workflow, 'nodes') else 'N/A'}")
        print(f"   - Edges: {len(workflow.edges) if hasattr(workflow, 'edges') else 'N/A'}")

        print(f"\n🔧 Checkpointer:")
        print(f"   - Type: {type(checkpointer).__name__}")

        print("\n" + "=" * 60)
        print("✅ All components loaded successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error loading workflow: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
