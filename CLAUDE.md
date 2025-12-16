# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ScholarFlow** is an intelligent academic literature presentation generator using a LangGraph-based workflow. The system transforms PDF papers into professional presentation slides through a multi-stage pipeline with human-in-the-loop review capabilities.

## Architecture

### Core Technology Stack
- **Backend**: Python 3.12+ with LangGraph for workflow orchestration
- **LLM**: OpenAI-compatible API (DeepSeek, Kimi, etc.)
- **PDF Parsing**: MinerU (Magic-PDF) for extracting structured content
- **Rendering**: Marp CLI (via npm) for generating presentations
- **Frontend**: React + TypeScript with LangGraph JS SDK
- **State Persistence**: SQLite-backed checkpointer for workflow resumability
- **Package Manager**: uv for Python dependencies

### LangGraph Workflow Pipeline

The system uses a **StateGraph** workflow defined in `app/graph/workflow.py:59`. The workflow consists of these sequential nodes:

1. **initialize** → Validates inputs and creates task state
2. **parse_pdf** → Extracts Markdown and images from PDF via MinerU
3. **split_markdown** → Chunks text for LLM processing
4. **stage1_process** → Generates slide outlines per chunk (with loop for parallel processing)
5. **merge_outlines** → Combines chunk outlines into unified structure
6. **human_review** → Pauses for user approval (optional)
7. **process_feedback** → Handles user edits and routing decisions
8. **stage2_process** → Converts approved outline to Marp Markdown
9. **render** → Generates final presentation file (PPTX/PDF/HTML)
10. **handle_error** → Error recovery and retry logic

**Key Workflow Features**:
- State is defined by `WorkflowState` TypedDict in `app/graph/state.py:64`
- Conditional edges route based on status (TaskStatus enum: app/graph/state.py:10)
- Checkpointer enables pause/resume at any node
- Parallel Stage 1 processing with loop-back for multiple chunks

### Directory Structure

```
ScholarFlow/
├── app/
│   ├── graph/              # LangGraph workflow definition
│   │   ├── workflow.py     # Main graph compilation (app/graph/workflow.py:145)
│   │   ├── state.py        # State schema & TaskStatus enum
│   │   └── nodes/          # Individual workflow nodes
│   ├── services/
│   │   ├── parser/         # PDF extraction (MinerU client)
│   │   ├── llm/            # Text splitting, merging, LLM provider
│   │   │   ├── split.py    # Markdown chunking logic
│   │   │   ├── merge.py    # Outline merging
│   │   │   ├── provider.py # LLM API wrapper
│   │   │   └── prompts/    # Stage 1/2 prompt templates
│   │   └── renderer/       # Marp rendering
│   ├── storage/            # State persistence layer
│   │   ├── checkpointer.py # LangGraph checkpointer implementation
│   │   ├── local_storage.py # JSON-based storage backend
│   │   └── interface.py    # Storage abstraction
│   ├── api/                # FastAPI endpoints
│   │   ├── endpoints.py    # Workflow API routes
│   │   ├── upload.py       # PDF upload handler
│   │   └── main.py         # FastAPI app entry
│   └── core/
│       ├── config.py       # Settings from env vars (app/core/config.py:26)
│       └── logger.py       # Logging configuration
├── frontend/               # React frontend (separate service)
├── tests/                  # Test suite
├── data/                   # Working directories
│   ├── inputs/            # Uploaded PDFs
│   ├── intermediate/      # MinerU output (Markdown + images)
│   ├── outputs/           # Generated presentations
│   └── workflows/         # Workflow state persistence
│       ├── checkpoints.db # SQLite database for LangGraph checkpoints
│       └── tasks/         # JSON snapshots for quick access
├── langgraph_server.py    # LangGraph server entry point
└── langgraph.json         # LangGraph deployment config
```

## Development Commands

### Environment Setup
```bash
# Install dependencies (includes langgraph-checkpoint-sqlite and aiosqlite)
uv sync

# Create .env from template
cp .env.example .env
# Edit .env with API keys (LLM_API_KEY, MINERU_API_KEY, etc.)
```

**Key Dependencies**:
- `langgraph>=1.0.4` - Workflow orchestration framework
- `langgraph-checkpoint-sqlite>=3.0.1` - SQLite-based checkpoint storage
- `aiosqlite>=0.20.0` - Async SQLite driver
- `fastapi>=0.100.0` - REST API framework
- `langchain-openai>=1.1.0` - LLM provider interface

### Running Services

**LangGraph Server** (workflow backend):
```bash
# Production mode (uses checkpointer)
python langgraph_server.py --host 0.0.0.0 --port 8123

# Or via LangGraph CLI
langgraph dev
```

**FastAPI Server** (file upload/download):
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (React app):
```bash
cd frontend
npm install
npm run dev  # Runs on port 3000
```

**Marp CLI** (required for rendering):
```bash
npm install -g @marp-team/marp-cli
```

### Testing

Run all tests:
```bash
pytest
# Or use the provided script
./run_tests.sh
```

Run specific test files:
```bash
pytest tests/test_workflow.py -v
pytest tests/test_async_llm.py -v
pytest tests/test_storage.py -v
```

Run with markers:
```bash
pytest -m unit           # Only unit tests
pytest -m integration    # Only integration tests
pytest -m "not slow"     # Skip slow tests
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

**Test Configuration**: `pyproject.toml:28` defines pytest settings including async mode and markers.

## Key Implementation Details

### Workflow State Management

**State Schema** (`app/graph/state.py:64`):
- The `WorkflowState` TypedDict contains 30+ fields tracking all pipeline data
- Fields include: task metadata, parsing results, chunks, LLM outputs, review data, errors
- State flows through nodes and is updated via return values
- Checkpointer persists state to SQLite database at `data/workflows/checkpoints.db`
- Additional JSON snapshots are stored in `data/workflows/tasks/{task_id}.json` for quick access

**Creating Initial State**:
```python
from app.graph.state import create_initial_state, PresentationStyle

state = create_initial_state(
    task_id="unique-id",
    pdf_path="/path/to/paper.pdf",
    presentation_style=PresentationStyle.ACADEMIC.value,
    max_chars=6000,
    target_chunks=6,
)
```

### Running the Workflow

**Async execution** (recommended):
```python
from app.graph.workflow import run_workflow

final_state = await run_workflow(
    initial_state=state,
    thread_id="my-thread-123"  # Optional, defaults to task_id
)
```

**Resuming after human review**:
```python
from app.graph.workflow import resume_workflow

final_state = await resume_workflow(
    task_id="my-thread-123",
    human_feedback={
        "approved": True,
        "comments": "Looks good!"
    }
)
```

### LLM Provider Configuration

The system supports any OpenAI-compatible API via `app/services/llm/provider.py`. Configure in `.env`:

```bash
# Use DeepSeek
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# Or use Kimi (Paratera endpoint)
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://llmapi.paratera.com/v1
LLM_MODEL=Kimi-K2
```

Settings are loaded via `app/core/config.py:53` with fallbacks to OPENAI_* or DEEPSEEK_* env vars.

### Text Splitting Algorithm

**Implementation**: `app/services/llm/split.py`

The splitter:
1. Parses Markdown headers (#, ##, ###) to identify sections
2. Groups content under each header
3. Breaks sections > `max_chars` into paragraphs
4. Optionally merges chunks to reach `target_chunks` count

Usage:
```python
from app.services.llm.split import split_markdown, merge_chunks

chunks = split_markdown(markdown_text, max_chars=6000)
merged = merge_chunks(chunks, target_count=6)
```

### Stage 1/2 Prompts

**Location**: `app/services/llm/prompts/prompt_templates.py`

- **Stage 1**: Generates slide outlines from Markdown chunks (supports 3 styles: academic/popular/business)
- **Stage 2**: Converts merged outline to Marp Markdown with CSS styling
- Detailed prompt specifications are in `app/services/llm/prompts/Prompt 模板清单.md`

Prompts are formatted at runtime with style and content parameters.

### Checkpointer Implementation

**Primary Storage**: SQLite database via `langgraph-checkpoint-sqlite`
**Secondary Storage**: JSON files in `app/storage/local_storage.py`
**Checkpointer**: `app/storage/checkpointer.py:get_checkpointer()`

The checkpointer enables workflow pause/resume by persisting state after each node execution. The system uses a dual-storage approach:

1. **SQLite Database** (`data/workflows/checkpoints.db`): LangGraph's native checkpoint storage for workflow state versioning and resumption
2. **JSON Files** (`data/workflows/tasks/{task_id}.json`): Quick-access snapshots for task metadata and status queries

**Key Methods**:
- `save_state(task_id, state, node_name)` - Persist state snapshot to JSON
- `load_state(task_id)` - Retrieve latest state snapshot from JSON
- `list_tasks(status, limit)` - List all tasks with optional status filter
- `delete_task(task_id)` - Delete a task's state
- `saver` property - Get the underlying LangGraph checkpointer (SqliteSaver)

**Usage**:
```python
from app.storage.checkpointer import get_checkpointer

# Get global checkpointer instance
checkpointer = get_checkpointer()

# Use in workflow compilation
from app.graph.workflow import create_workflow
workflow = create_workflow()
compiled = workflow.compile(checkpointer=checkpointer.saver)

# Close when done (cleanup resources)
checkpointer.close()
```

**Note**: The SQLite database file is created automatically on first use. No additional database server setup is required.

### Marp Rendering

**Engine**: `app/services/renderer/marp_engine.py:9`

Wraps Marp CLI to generate presentations from Markdown:
```python
from app.services.renderer.marp_engine import render_marp

output_path = render_marp(
    marp_markdown_path="/path/to/slides.md",
    output_format="pptx",  # or "pdf", "html"
    theme_css_path="/path/to/custom.css"  # optional
)
```

Custom CSS themes are stored in `app/services/renderer/styles/`.

### Image Tokenization Protection

**Problem**: LLM processing often corrupts image hash values, causing final presentations to display broken images.

**Solution**: Three-stage tokenization protection mechanism implemented in `app/services/parser/image_manager.py`:

#### Stage 1: Tokenize After PDF Parsing
Immediately after MinerU extracts Markdown, replace image references with simple tokens:

```python
from app.services.parser.image_manager import ImageManager

manager = ImageManager(Path("data/intermediate"))

# Convert: ![alt](images/hash.jpg) → [[TOKEN_IMG_001]]
tokenized_text, token_map = manager.tokenize_image_references_enhanced(
    markdown_content=markdown,
    task_id="task_123"
)
```

**Token Map Structure**:
```python
{
    "[[TOKEN_IMG_001]]": {
        "hash": "df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0",
        "alt_text": "Figure 1: CIFAR-10 results",
        "original_path": "images/df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg",
        "filename": "df31c4889a278a680daa11239dcc9df51b4c7fd8b86edfa336bc2b3dec9e25d0.jpg"
    }
}
```

#### Stage 2: LLM Processing with Token Protection
LLM processes simple tokens (`[[TOKEN_IMG_001]]`) instead of complex hash paths. Updated prompts in `app/services/llm/prompts/prompt_templates.py` explicitly forbid:
- Modifying token numbers
- Converting tokens to other formats
- Deleting or omitting tokens
- Expanding tokens to full image paths

#### Stage 3: Restore Before Rendering
Before Marp rendering, restore tokens to proper image links:

```python
# Convert: [[TOKEN_IMG_001]] → ![Figure 1](images/hash.jpg)
final_markdown = manager.restore_tokens_to_markdown_enhanced(
    tokenized_content=tokenized_markdown,
    token_map=token_map,
    output_format='marp'
)
```

**Integration Points**:
- **PDF Parsing Node** (`app/graph/nodes/pdf_parsing.py`): Tokenizes immediately after MinerU extraction
- **Rendering Node** (`app/graph/nodes/rendering.py`): Restores tokens before Marp rendering
- **WorkflowState** (`app/graph/state.py`): Added `tokenized_text`, `image_token_map`, `token_count` fields

**Testing**: Run `pytest tests/test_tokenization.py -v` to verify tokenization mechanism.

**Benefits**:
- ✅ 100% image preservation - no broken links in final PPT
- ✅ Automatic - no manual intervention required
- ✅ Traceable - token map records all image metadata
- ✅ LLM-safe - simple tokens resist modification

## Common Development Patterns

### Adding a New Workflow Node

1. Create node file in `app/graph/nodes/my_node.py`:
```python
from app.graph.state import WorkflowState, TaskStatus

def node_my_operation(state: WorkflowState) -> WorkflowState:
    """Process state and return updates."""
    # Extract needed data
    data = state.get("some_field")

    # Perform operation
    result = process(data)

    # Return state updates
    return {
        "status": TaskStatus.NEXT_STAGE.value,
        "result_field": result,
        "updated_at": datetime.now().isoformat(),
    }
```

2. Register in `app/graph/workflow.py:59`:
```python
workflow.add_node("my_operation", node_my_operation)
workflow.add_edge("previous_node", "my_operation")
```

### Adding New LLM Prompts

1. Update `app/services/llm/prompts/prompt_templates.py` with new template string
2. Use in workflow node:
```python
from app.services.llm.provider import call_model
from app.services.llm.prompts.prompt_templates import MY_PROMPT

response = await call_model(
    prompt=MY_PROMPT.format(content=chunk_text, style=style),
    max_tokens=4000,
)
```

### Extending State Schema

1. Add field to `WorkflowState` in `app/graph/state.py:64`:
```python
class WorkflowState(TypedDict, total=False):
    # Existing fields...
    my_new_field: str  # Add new field
```

2. Update `create_initial_state()` to initialize the field
3. Nodes can now read/write this field

## API Integration

### FastAPI Endpoints

**Upload PDF** (`app/api/upload.py`):
```
POST /api/upload
Content-Type: multipart/form-data
Body: file (PDF)
Returns: {"filename": "...", "path": "..."}
```

**Start Workflow** (`app/api/endpoints.py`):
```
POST /api/tasks
Body: {
  "pdf_path": "/path/to/file.pdf",
  "presentation_style": "academic",
  "max_chars": 6000,
  "target_chunks": 6
}
Returns: {"task_id": "...", "status": "pending"}
```

**Check Status**:
```
GET /api/tasks/{task_id}
Returns: WorkflowState (full state object)
```

### LangGraph SDK (Frontend)

The React frontend uses LangGraph JS SDK to interact with the workflow server at `localhost:8123`. See `frontend/src/lib/langgraph.ts` for client configuration.

## Environment Variables

Required variables in `.env`:

```bash
# LLM Configuration (OpenAI-compatible)
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.example.com/v1
LLM_MODEL=model-name
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7

# MinerU Configuration
MINERU_API_KEY=xxx
MINERU_ENDPOINT=https://api.opendatalab.org.cn

# Storage
STORAGE_BACKEND=local  # or 's3'
DATA_DIR=data          # Working directory

# Server Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
LANGGRAPH_HOST=0.0.0.0
LANGGRAPH_PORT=8123

# LangSmith Tracing (optional)
LANGSMITH_API_KEY=lsv2_xxx
LANGCHAIN_TRACING_V2=true
```

## Troubleshooting

**Workflow not resuming**: Ensure checkpointer is enabled in `compile_workflow(with_checkpointer=True)` and thread_id is consistent. Check that `data/workflows/checkpoints.db` exists and is writable.

**SQLite database errors**: If you see "unable to open database file", ensure:
  - The `data/workflows/` directory exists and has write permissions
  - No other process is locking the database file
  - Disk space is available

**MinerU connection error**: Verify MINERU_API_KEY and MINERU_ENDPOINT are correct. Check API quota.

**LLM API errors**: Confirm LLM_API_KEY, LLM_BASE_URL, and LLM_MODEL are properly set. Check rate limits.

**Marp rendering fails**: Ensure `@marp-team/marp-cli` is installed globally: `npm install -g @marp-team/marp-cli`

**Import errors**: Activate venv or use `uv run`: `source .venv/bin/activate` or `uv run python script.py`

**Test failures**: Run `pytest -v` to see detailed errors. Check async tests use `pytest-asyncio` markers.

**Missing checkpoint dependencies**: If you see ImportError for langgraph-checkpoint-sqlite, run: `uv add langgraph-checkpoint-sqlite aiosqlite`

## Important Notes

- The workflow is **asynchronous** by design. Use `await` with all workflow operations.
- **State persistence** is critical for human-in-the-loop. Always use consistent `thread_id`.
- **SQLite checkpointer** is used for reliable state persistence. The database file (`data/workflows/checkpoints.db`) is created automatically and should be included in backups for production deployments.
- **Dual storage**: LangGraph uses SQLite for checkpoint versioning, while JSON files provide quick task metadata access without database queries.
- **Error handling** is centralized in the `handle_error` node with retry logic.
- **Parallel processing** in Stage 1 is managed via loop-back edges, not multi-threading.
- The system supports **three presentation styles** (academic/popular/business) defined in `app/graph/state.py:26`.
- **Image references** from MinerU are preserved as URLs throughout the pipeline.

代码运行与预期不符应该直接抛出异常，方便开发调试