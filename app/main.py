"""ScholarFlow main entry point with CLI and API server.

Usage:
    # CLI mode - split markdown
    python -m app.main --md-path path/to/file.md --max-chars 8000 --target-chunks 3

    # API server mode
    python -m app.main serve --host 0.0.0.0 --port 8000

    # LangGraph server mode
    python -m app.main langgraph --host 0.0.0.0 --port 8123

    # Run both servers
    python -m app.main both --fastapi-port 8000 --langgraph-port 8123
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from app.services.llm.split import DEFAULT_MAX_CHARS, merge_chunks, split_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ScholarFlow - Academic Paper to Presentation")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Split command (default behavior)
    split_parser = subparsers.add_parser("split", help="Split a Markdown file for outline generation")
    split_parser.add_argument(
        "--md-path",
        type=Path,
        required=True,
        help="Path to the input Markdown file (MinerU output).",
    )
    split_parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Maximum characters per chunk; defaults to internal constant if omitted.",
    )
    split_parser.add_argument(
        "--target-chunks",
        type=int,
        default=None,
        help="Optional upper bound on number of chunks after merging.",
    )
    split_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write resulting chunks as JSON.",
    )

    # Serve command (FastAPI server)
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    serve_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # LangGraph server command
    langgraph_parser = subparsers.add_parser("langgraph", help="Start the LangGraph server")
    langgraph_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    langgraph_parser.add_argument(
        "--port",
        type=int,
        default=8123,
        help="Port to bind to (default: 8123)",
    )

    # Both servers command
    both_parser = subparsers.add_parser("both", help="Start both FastAPI and LangGraph servers")
    both_parser.add_argument(
        "--fastapi-host",
        type=str,
        default="0.0.0.0",
        help="FastAPI host (default: 0.0.0.0)",
    )
    both_parser.add_argument(
        "--fastapi-port",
        type=int,
        default=8000,
        help="FastAPI port (default: 8000)",
    )
    both_parser.add_argument(
        "--langgraph-host",
        type=str,
        default="0.0.0.0",
        help="LangGraph host (default: 0.0.0.0)",
    )
    both_parser.add_argument(
        "--langgraph-port",
        type=int,
        default=8123,
        help="LangGraph port (default: 8123)",
    )
    both_parser.add_argument(
        "--fastapi-reload",
        action="store_true",
        help="Enable auto-reload for FastAPI development",
    )

    # Legacy arguments for backward compatibility (when no subcommand)
    parser.add_argument(
        "--md-path",
        type=Path,
        default=None,
        help="Path to the input Markdown file (MinerU output).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Maximum characters per chunk.",
    )
    parser.add_argument(
        "--target-chunks",
        type=int,
        default=None,
        help="Optional upper bound on number of chunks.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write resulting chunks as JSON.",
    )

    return parser.parse_args()


def load_markdown(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {path}")
    return path.read_text(encoding="utf-8")


def run_split(md_path: Path, max_chars: int | None, target_chunks: int | None) -> List[Dict[str, Any]]:
    markdown_text = load_markdown(md_path)
    max_chars_value = max_chars if (max_chars and max_chars > 0) else DEFAULT_MAX_CHARS
    chunks = split_markdown(markdown_text, max_chars=max_chars_value)
    return merge_chunks(chunks, target_count=target_chunks)


def create_app():
    """Create FastAPI application with API routes and upload endpoints."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.tasks import router as tasks_router
    from app.api.upload import router as upload_router

    app = FastAPI(
        title="ScholarFlow API",
        description="Academic Paper to Presentation Generator",
        version="2.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    app.include_router(tasks_router)
    app.include_router(upload_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "2.0.0"}

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "ScholarFlow API",
            "version": "2.0.0",
            "docs": "/docs",
            "endpoints": {
                "upload_pdf": "POST /api/upload",
                "download_result": "GET /api/download/{task_id}",
                "create_task": "POST /api/tasks",
                "get_status": "GET /api/tasks/{task_id}/status",
                "get_result": "GET /api/tasks/{task_id}/result",
                "submit_feedback": "POST /api/tasks/{task_id}/human-feedback",
                "list_tasks": "GET /api/tasks",
            },
        }

    return app


def run_server(host: str, port: int, reload: bool = False):
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run(
        "app.main:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )


def run_langgraph_server(host: str, port: int):
    """Run the LangGraph server."""
    from langgraph_sdk.server import run_server
    from app.graph.workflow import get_workflow
    from app.storage.checkpointer import get_checkpointer

    workflow = get_workflow()
    checkpointer = get_checkpointer()

    run_server(
        workflows={"scholarflow": workflow},
        checkpointer=checkpointer,
        host=host,
        port=port,
    )


def run_both_servers(fastapi_host: str, fastapi_port: int, langgraph_host: str, langgraph_port: int, fastapi_reload: bool = False):
    """Run both FastAPI and LangGraph servers concurrently."""
    import threading
    import uvicorn
    from langgraph_sdk.server import run_server
    from app.graph.workflow import get_workflow
    from app.storage.checkpointer import get_checkpointer

    print(f"Starting ScholarFlow servers...")
    print(f"  FastAPI: http://{fastapi_host}:{fastapi_port}")
    print(f"  LangGraph: http://{langgraph_host}:{langgraph_port}")

    # Start FastAPI server in a thread
    def start_fastapi():
        uvicorn.run(
            "app.main:create_app",
            host=fastapi_host,
            port=fastapi_port,
            reload=fastapi_reload,
            factory=True,
        )

    fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()

    # Start LangGraph server in main thread
    workflow = get_workflow()
    checkpointer = get_checkpointer()

    run_server(
        workflows={"scholarflow": workflow},
        checkpointer=checkpointer,
        host=langgraph_host,
        port=langgraph_port,
    )


def main() -> None:
    args = parse_args()

    if args.command == "serve":
        # Start FastAPI server
        run_server(args.host, args.port, args.reload)
    elif args.command == "langgraph":
        # Start LangGraph server
        run_langgraph_server(args.host, args.port)
    elif args.command == "both":
        # Start both servers
        run_both_servers(
            args.fastapi_host,
            args.fastapi_port,
            args.langgraph_host,
            args.langgraph_port,
            args.fastapi_reload
        )
    elif args.command == "split" or args.md_path:
        # Split markdown (legacy or explicit command)
        md_path = args.md_path
        if not md_path:
            print("Error: --md-path is required for split command")
            return

        chunks = run_split(md_path, args.max_chars, args.target_chunks)

        if args.output:
            args.output.write_text(
                json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Wrote chunks to {args.output}")
        else:
            print(json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2))
    else:
        # No command specified, show help
        print("ScholarFlow - Academic Paper to Presentation Generator")
        print()
        print("Usage:")
        print("  python -m app.main serve                            # Start FastAPI server")
        print("  python -m app.main langgraph                        # Start LangGraph server")
        print("  python -m app.main both                             # Start both servers")
        print("  python -m app.main split --md-path file.md          # Split markdown")
        print()
        print("Run with --help for more options")


if __name__ == "__main__":
    main()
