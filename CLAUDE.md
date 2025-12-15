# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ScholarFlow** is an intelligent academic literature presentation generator that transforms PDF papers into professional presentation slides. The system uses a three-stage pipeline:

1. **Parse**: MinerU extracts structured content (Markdown + images) from PDF papers
2. **LLM Processing**: DeepSeek processes content, splits it into chunks, generates outlines
3. **Render**: Marp converts Markdown to presentation formats (PPTX/PDF/HTML)

The project supports three presentation styles: Academic, Popular Science, and Business Pitch.

## Development Setup

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Marp CLI (`npm install -g @marp-team/marp-cli`)
- Docker (for MinerU service)

### Installation
```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys and endpoints

# Start MinerU service (optional, for PDF parsing)
docker-compose up -d mineru
```

### Environment Variables (.env)
```
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
MINERU_ENDPOINT=http://localhost:9000
OSS_ENDPOINT=http://localhost:9001
OSS_BUCKET=your-bucket
```

## Common Commands

### CLI Usage
Split Markdown into chunks for processing:
```bash
python -m app.main --md-path data/intermediate/paper.md --max-chunks 6000 --target-chunks 6
```

### Testing
```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_split.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### Development
```bash
# Install Marp CLI for rendering
npm install -g @marp-team/marp-cli

# Render a presentation
marp presentation.md --output presentation.html

# Install new dependencies
uv add package-name

# Update dependencies
uv sync
```

## Code Architecture

### Directory Structure
```
ScholarFlow/
├── app/                    # Core application
│   ├── core/              # Infrastructure (config, logging)
│   │   ├── config.py      # Environment settings (app/core/config.py:12)
│   │   └── logger.py      # Logging configuration
│   ├── api/               # FastAPI endpoints (placeholder)
│   │   ├── endpoints.py   # API routes
│   │   └── models.py      # Data models
│   ├── main.py           # CLI entry point
│   └── services/         # Business logic
│       ├── parser/       # PDF parsing
│       │   ├── mineru_client.py    # MinerU integration (app/services/parser/mineru_client.py:8)
│       │   └── oss_uploader.py     # Image upload
│       ├── llm/          # LLM processing
│       │   ├── text_splitter.py    # Core splitting logic (app/services/llm/text_splitter.py:7)
│       │   ├── outline_merger.py   # Chunk merging
│       │   ├── provider.py         # DeepSeek/OpenAI wrapper
│       │   └── prompts/           # Prompt templates
│       │       ├── prompt_templates.py
│       │       └── Prompt 模板清单.md  # Stage 1 & 2 prompts
│       └── renderer/     # Presentation rendering
│           ├── marp_engine.py      # Marp CLI wrapper (app/services/renderer/marp_engine.py:9)
│           └── styles/            # CSS themes
├── data/                 # Data directories
│   ├── inputs/          # Uploaded PDFs
│   ├── intermediate/    # MinerU output (Markdown + images)
│   └── outputs/         # Final presentations
├── tests/               # Unit tests
│   └── test_split.py    # Splitter tests
└── docker-compose.yml   # MinerU service
```

### Core Components

**1. Text Splitter** (`app/services/llm/text_splitter.py:7`)
- Splits Markdown into manageable chunks (default 6000 chars)
- Preserves section hierarchy with titles
- Merges chunks to target count for LLM processing
- Entry point: `main()` function (app/services/llm/text_splitter.py:157)

**2. MinerU Client** (`app/services/parser/mineru_client.py:8`)
- Placeholder for PDF to Markdown conversion
- Returns: (markdown_text, image_paths)
- Currently raises NotImplementedError - needs integration

**3. Marp Engine** (`app/services/renderer/marp_engine.py:9`)
- Wraps Marp CLI for rendering
- Command: `marp input.md --output output_path [--theme theme.css]`
- Supports custom CSS themes

**4. Configuration** (`app/core/config.py:12`)
- Settings dataclass loads from environment variables
- Cached with `@lru_cache` for performance

### Key Workflows

**CLI Workflow** (app/main.py:1):
```python
# Split markdown into chunks
python -m app.main --md-path file.md --max-chars 6000 --target-chunks 6
```

**Service Integration**:
```
PDF → MinerU → Markdown + Images → Text Splitter → Chunks → LLM → Outline → Marp → Presentation
```

**Prompt System** (app/services/llm/prompts/Prompt 模板清单.md):
- Stage 1: Generates slide outlines (3 styles: academic/popular/business)
- Stage 2: Converts outlines to Marp Markdown
- Prompts handle chunk拼接 and image references

## Important Implementation Details

### Text Splitting Algorithm
The splitter (app/services/llm/text_splitter.py:7):
1. Parses Markdown headers (#, ##) to identify sections
2. Groups content under each header
3. Breaks sections > max_chars into paragraphs
4. Merges adjacent chunks if target count is lower

### Image Handling
- MinerU extracts images to cloud storage (OSS/S3)
- Images referenced by URL in Markdown: `![alt](https://...url)`
- Prompts preserve image links in slide outlines

### LLM Integration
- Uses DeepSeek API (configurable via env vars)
- LangChain for framework
- Two-stage processing: outline → Marp conversion

## Development Notes

### Current Status
- ✅ Text splitting/merging logic implemented
- ✅ Prompt templates designed
- ❌ MinerU integration (placeholder only)
- ❌ LLM provider integration
- ❌ OSS uploader implementation
- ❌ Full pipeline integration
- ❌ API endpoints implementation

### Testing
- Only `test_split.py` exists currently
- Tests splitting behavior with sample Markdown
- Use `pytest` to run tests

### Data Flow
1. Upload PDF to `data/inputs/`
2. MinerU parses to `data/intermediate/paper.md`
3. Text splitter creates chunks
4. LLM processes chunks → outline
5. Marp renders → `data/outputs/presentation.html`

### Adding New Features
- **New LLM provider**: Implement in `app/services/llm/provider.py`
- **New presentation style**: Add CSS theme to `app/services/renderer/styles/`
- **New prompt template**: Add to `app/services/llm/prompts/`
- **API endpoints**: Implement in `app/api/endpoints.py`

## Dependencies

**Core**: FastAPI, uvicorn, pydantic, openai, langchain, langgraph
**Build**: uv (Python package manager)
**Rendering**: @marp-team/marp-cli (npm)
**Services**: MinerU (docker), Object Storage (OSS/S3)

## Troubleshooting

**MinerU Connection Error**: Ensure docker-compose service is running
**Missing API Key**: Check `.env` file is properly configured
**Marp Rendering Fails**: Verify Marp CLI is installed (`marp --version`)
**Import Errors**: Activate virtual environment (`source .venv/bin/activate`)

## References

- MinerU: https://github.com/opendatalab/MinerU
- DeepSeek API: https://platform.deepseek.com/
- Marp: https://marp.app/
- Project Structure: See PROJECT_STRUCTURE.md
- Full Documentation: See README.md
