"""LLM Call Logger for debugging and monitoring."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class LLMCallLogger:
    """Logs LLM calls with input, prompt, and output for debugging."""

    def __init__(self, task_id: str, log_dir: Optional[Path] = None):
        """Initialize logger.

        Args:
            task_id: Unique task identifier
            log_dir: Directory to store logs. If None, uses data/logs/{task_id}
        """
        self.task_id = task_id
        self.log_dir = log_dir or Path("data") / "logs" / task_id
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = self.log_dir / "llm_calls.md"
        self.json_log_file = self.log_dir / "llm_calls.json"

        # Initialize markdown file
        self._init_markdown_log()

    def _init_markdown_log(self):
        """Initialize the markdown log file with header."""
        header = f"""# LLM 调用日志

## 任务信息

- **任务ID**: {self.task_id}
- **开始时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **日志文件**: {self.log_file}

---

## LLM 调用记录

"""
        self.log_file.write_text(header, encoding="utf-8")

    def log_call(
        self,
        step_name: str,
        prompt: str,
        model: str,
        response: Dict[str, Any],
        max_chars: int = 2000,
    ):
        """Log an LLM call with input, prompt, and output.

        Args:
            step_name: Name of the step (e.g., "Generate Outline")
            prompt: The full prompt sent to the LLM
            model: Model name used
            response: Response from the LLM
            max_chars: Maximum characters to log for prompt/response (default: 2000)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Prepare content (truncate if too long)
        prompt_display = prompt[:max_chars] + "..." if len(prompt) > max_chars else prompt
        response_content = response.get("content", "")
        response_display = response_content[:max_chars] + "..." if len(response_content) > max_chars else response_content

        # Create markdown entry
        entry = f"""### {step_name}

**时间**: {timestamp}
**模型**: {model}
**Token使用**: {response.get('usage', {})}

#### 输入提示词

```markdown
{prompt_display}
```

#### 模型输出

```markdown
{response_display}
```

#### 完整响应

```json
{json.dumps(response, ensure_ascii=False, indent=2)}
```

---

"""

        # Append to markdown file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)

        # Also log to JSON for programmatic access
        json_entry = {
            "timestamp": timestamp,
            "step_name": step_name,
            "model": model,
            "prompt": prompt,
            "response": response,
            "usage": response.get("usage", {}),
        }

        # Load existing JSON log
        if self.json_log_file.exists():
            try:
                logs = json.loads(self.json_log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logs = []
        else:
            logs = []

        logs.append(json_entry)

        # Write back
        self.json_log_file.write_text(
            json.dumps(logs, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"📝 Logged LLM call: {step_name}")

    def log_summary(self, summary: str):
        """Add a summary section to the log.

        Args:
            summary: Summary text to add
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        summary_entry = f"""

---

## 执行总结

**完成时间**: {timestamp}

{summary}

"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(summary_entry)

    def get_log_path(self) -> Path:
        """Get the path to the markdown log file.

        Returns:
            Path to the log file
        """
        return self.log_file

    def get_json_log_path(self) -> Path:
        """Get the path to the JSON log file.

        Returns:
            Path to the JSON log file
        """
        return self.json_log_file


def create_logger(task_id: str, log_dir: Optional[Path] = None) -> LLMCallLogger:
    """Create an LLMCallLogger instance.

    Args:
        task_id: Task identifier
        log_dir: Optional custom log directory

    Returns:
        LLMCallLogger instance
    """
    return LLMCallLogger(task_id, log_dir)
