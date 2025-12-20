# ScholarFlow - GEMINI.md

This file provides context and instructions for the Gemini agent working on the ScholarFlow project.

## Project Overview

**ScholarFlow** is an intelligent agent system designed to transform academic PDF literature into professional presentation slides. It leverages a **LangGraph-based workflow** to orchestrate a multi-stage pipeline involving:
1.  **PDF Parsing**: High-fidelity extraction using MinerU.
2.  **Intelligent Processing**: LLM-driven summarization and content generation (DeepSeek/OpenAI-compatible).
3.  **Human-in-the-loop**: Interactive review steps for user control.
4.  **Rendering**: Automated slide generation using Marp (Markdown Presentation Ecosystem).

## Architecture

### Tech Stack
*   **Backend**: Python 3.12+
    *   **Framework**: LangGraph (workflow orchestration), FastAPI (REST API).
    *   **Dependency Manager**: `uv`.
    *   **State Persistence**: `langgraph-checkpoint-sqlite` (SQLite database).
    *   **Testing**: `pytest` with `pytest-asyncio`.
*   **Frontend**: TypeScript, React, Next.js 15+
    *   **UI Library**: Shadcn UI, Tailwind CSS.
    *   **Client SDK**: `@langchain/langgraph-sdk`.
    *   **Package Manager**: `npm`.
*   **External Tools**:
    *   **MinerU**: PDF parsing engine.
    *   **Marp CLI**: Slide rendering engine.

### Data Pipeline
The core logic is defined in a `StateGraph` (`app/graph/workflow.py`) with the following flow:
1.  **`initialize`**: Setup task state.
2.  **`parse_pdf`**: Extract text and images (MinerU). *Critical: Images are tokenized here to prevent LLM hallucination.*
3.  **`split_markdown`**: Chunk text for processing.
4.  **`stage1_process`**: Generate slide outlines (parallel processing via loop-back).
5.  **`merge_outlines`**: Combine chunks into a unified outline.
6.  **`human_review`**: **Breakpoint**. Waits for user approval/edits.
7.  **`stage2_process`**: Expand outline into full Marp-compatible Markdown.
8.  **`render`**: Generate final output (PPTX/PDF/HTML).

## Key File Locations

| Category | Description | Path |
| :--- | :--- | :--- |
| **Workflow** | Main graph definition | `app/graph/workflow.py` |
| | State schema & Enums | `app/graph/state.py` |
| | Individual Nodes | `app/graph/nodes/` |
| **Services** | LLM Provider & Prompts | `app/services/llm/` |
| | PDF Parsing (MinerU) | `app/services/parser/` |
| | Image Protection | `app/services/parser/image_manager.py` |
| | Marp Renderer | `app/services/renderer/marp_engine.py` |
| **API** | FastAPI Entry | `app/api/main.py` |
| | Endpoints | `app/api/` |
| **Frontend** | Main Page | `frontend/src/app/page.tsx` |
| | Components | `frontend/src/components/` |
| **Config** | Settings & Env | `app/core/config.py` |

## Development Workflow

### Prerequisites
*   Python 3.12+
*   Node.js & npm
*   Marp CLI (`npm install -g @marp-team/marp-cli`)
*   `uv` (Python package manager)

### Installation
1.  **Backend**:
    ```bash
    uv sync
    cp .env.example .env  # Configure LLM_API_KEY, MINERU_API_KEY, etc.
    ```
2.  **Frontend**:
    ```bash
    cd frontend
    npm install
    ```

### Running Services
*   **LangGraph Server** (Workflow Engine):
    ```bash
    # Runs on port 8123
    python langgraph_server.py
    # OR
    langgraph dev
    ```
*   **FastAPI Server** (File Uploads/API):
    ```bash
    # Runs on port 8000
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
    ```
*   **Frontend**:
    ```bash
    cd frontend
    npm run dev
    # Runs on port 3000
    ```

### Testing
*   **Run All Tests**: `./run_tests.sh` or `pytest`
*   **Specific Test**: `pytest tests/test_workflow.py -v`
*   **Markers**: `pytest -m unit`, `pytest -m integration`

## Conventions & Best Practices

1.  **Async/Await**: The backend is heavily async. Ensure all I/O bound operations (LLM calls, DB access) are awaited.
2.  **State Management**:
    *   Use `WorkflowState` (TypedDict) for passing data between nodes.
    *   **Do not** modify state in place; return a dictionary of updates.
    *   Image tokens (e.g., `[[TOKEN_IMG_001]]`) are used to protect image paths during LLM processing.
3.  **Error Handling**:
    *   Errors should be caught and routed to the `handle_error` node where possible.
    *   Use the `TaskStatus.ERROR` enum value.
4.  **Frontend/Backend Contract**:
    *   Frontend uses `LangGraph SDK` to stream workflow events.
    *   File uploads are handled separately by FastAPI (`/api/upload`) before triggering the workflow.
