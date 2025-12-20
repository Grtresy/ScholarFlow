"""PDF parsing node for workflow."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.graph.state import TaskStatus, WorkflowState
from app.services.parser.mineru_client import MinerUClient
from app.services.parser.image_manager import ImageManager


def node_parse_pdf(state: WorkflowState) -> Dict[str, Any]:
    """Parse PDF using MinerU service.

    This node:
    - Calls MinerU API to convert PDF to Markdown
    - Extracts images
    - Saves intermediate results

    Args:
        state: Current workflow state

    Returns:
        State updates with markdown_text, image_paths, parse_metadata
    """
    pdf_path = Path(state["pdf_path"])
    task_id = state["task_id"]

    # Prepare output directory
    output_dir = Path("data/workflow/intermediate") / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize MinerU client
        client = MinerUClient()

        # Process PDF
        markdown_path, image_paths, metadata = client.process_pdf(
            pdf_path=pdf_path,
            model_version="vlm",
            output_dir=output_dir,
        )

        # Read markdown content
        markdown_text = markdown_path.read_text(encoding="utf-8")

        # Initialize ImageManager for tokenization
        image_manager = ImageManager(Path("data/workflow/intermediate"))
        task_dir = image_manager.create_task_dir(task_id)

        # Tokenize image references to protect hashes during LLM processing
        tokenized_text, image_token_map = image_manager.tokenize_image_references_enhanced(
            markdown_content=markdown_text,
            task_id=task_id
        )

        token_count = len(image_token_map)

        # Convert paths to strings
        image_path_strs = [str(p) for p in image_paths]

        # Log success
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "pdf_parsing",
            "message": f"PDF parsed successfully. {len(markdown_text)} chars, {len(image_path_strs)} images",
            "metadata": metadata,
        }

        execution_log = state.get("execution_log", [])
        execution_log.append(log_entry)

        return {
            "status": TaskStatus.SPLITTING.value,
            "markdown_text": markdown_text,
            "markdown_path": str(markdown_path),
            "image_paths": image_path_strs,
            "parse_metadata": metadata,
            # Token management
            "tokenized_text": tokenized_text,
            "image_token_map": image_token_map,
            "token_count": token_count,
            "current_step": f"PDF解析完成，共 {len(markdown_text)} 字符，{token_count} 张图片已Token化",
            "progress_percentage": 15.0,
            "updated_at": datetime.now().isoformat(),
            "execution_log": execution_log,
        }

    except FileNotFoundError as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"PDF file not found: {e}",
            "current_step": "PDF解析失败：文件未找到",
        }
    except ValueError as e:
        # MinerU API token missing
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"MinerU configuration error: {e}",
            "current_step": "PDF解析失败：MinerU配置错误",
        }
    except RuntimeError as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"PDF parsing failed: {e}",
            "current_step": f"PDF解析失败：{e}",
        }
    except Exception as e:
        return {
            "status": TaskStatus.FAILED.value,
            "error_message": f"Unexpected error during PDF parsing: {e}",
            "current_step": f"PDF解析失败：{e}",
        }
