"""Minimal CLI entry to split a Markdown file into chunks.

Usage:
    python -m app.main --md-path path/to/file.md --max-chars 6000 --target-chunks 6
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from app.services.llm.text_splitter import DEFAULT_MAX_CHARS, merge_chunks, split_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split a Markdown file for outline generation.")
    parser.add_argument(
        "--md-path",
        type=Path,
        required=True,
        help="Path to the input Markdown file (MinerU output).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="Maximum characters per chunk; defaults to internal constant if omitted.",
    )
    parser.add_argument(
        "--target-chunks",
        type=int,
        default=None,
        help="Optional upper bound on number of chunks after merging.",
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


def run(md_path: Path, max_chars: int | None, target_chunks: int | None) -> List[Dict[str, Any]]:
    markdown_text = load_markdown(md_path)
    max_chars_value = max_chars if (max_chars and max_chars > 0) else DEFAULT_MAX_CHARS
    chunks = split_markdown(markdown_text, max_chars=max_chars_value)
    return merge_chunks(chunks, target_count=target_chunks)


def main() -> None:
    args = parse_args()
    chunks = run(args.md_path, args.max_chars, args.target_chunks)

    if args.output:
        args.output.write_text(json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote chunks to {args.output}")
    else:
        print(json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
