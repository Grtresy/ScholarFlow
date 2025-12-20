#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.llm.merge import merge_outlines
from app.services.llm.prompts.prompt_templates import STAGE1_PROMPT, STAGE2_PROMPT
from app.services.llm.provider import LLMClient
from app.services.llm.split import DEFAULT_MAX_CHARS, merge_chunks, split_markdown
from app.services.parser.image_manager import ImageManager


def _capitalize_style(style: str) -> str:
    style = (style or "").strip()
    if not style:
        return style
    return style[:1].upper() + style[1:].lower()


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Markdown HITL workflow: split -> stage1 -> merge -> human edit -> stage2",
    )
    parser.add_argument("--md-path", type=Path, required=True, help="Path to MinerU markdown file.")
    parser.add_argument("--style", type=str, default="academic", help="Presentation style (academic/popular/business).")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS, help="Max chars per chunk.")
    parser.add_argument("--target-chunks", type=int, default=3, help="Optional upper bound for chunk count.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for artifacts.")
    parser.add_argument("--skip-human", action="store_true", help="Skip manual outline editing.")
    parser.add_argument("--no-tokenize", action="store_true", help="Do not tokenize image links.")
    parser.add_argument("--stage1-max-tokens", type=int, default=4000, help="Max tokens for Stage 1 calls.")
    parser.add_argument("--stage2-max-tokens", type=int, default=8000, help="Max tokens for Stage 2 calls.")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.md_path.is_file():
        print(f"Markdown file not found: {args.md_path}", file=sys.stderr)
        return 1

    run_id = datetime.now().strftime("md_hil_%Y%m%d_%H%M%S")
    out_dir = args.out_dir or Path("data/workflow/manual_hil") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    md_text = args.md_path.read_text(encoding="utf-8")
    style = _capitalize_style(args.style)

    tokenized_text = md_text
    token_map = {}
    if not args.no_tokenize and "[[TOKEN_IMG_" not in md_text:
        image_manager = ImageManager(Path("data/workflow/intermediate"))
        tokenized_text, token_map = image_manager.tokenize_image_references_enhanced(
            markdown_content=md_text,
            task_id=run_id,
        )
        _write_text(out_dir / "tokenized.md", tokenized_text)
        (out_dir / "token_map.json").write_text(
            json.dumps(token_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        _write_text(out_dir / "tokenized.md", tokenized_text)

    chunks = split_markdown(tokenized_text, max_chars=args.max_chars)
    if args.target_chunks and args.target_chunks > 0:
        chunks = merge_chunks(chunks, target_count=args.target_chunks)

    (out_dir / "chunks.json").write_text(
        json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    client = LLMClient()
    stage1_results = []

    for idx, chunk in enumerate(chunks, start=1):
        chunk_id = chunk.get("id", idx)
        chunk_title = chunk.get("title", f"Chunk {chunk_id}")
        chunk_text = chunk.get("text", "")

        print(f"[stage1] chunk {idx}/{len(chunks)}: {chunk_title}")
        prompt = STAGE1_PROMPT.format(style=style, content=chunk_text)
        response = client.complete(
            prompt=prompt,
            max_tokens=args.stage1_max_tokens,
            temperature=args.temperature,
        )
        outline = response.get("content", "")

        stage1_results.append(
            {
                "chunk_id": chunk_id,
                "chunk_title": chunk_title,
                "outline": outline,
                "success": True,
            }
        )

        _write_text(out_dir / f"stage1_chunk_{chunk_id:03d}.md", outline)

    (out_dir / "stage1_results.json").write_text(
        json.dumps(stage1_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    merged_outline = merge_outlines(stage1_results)
    raw_outline_path = out_dir / "merged_outline_raw.md"
    merged_outline_path = out_dir / "merged_outline.md"
    _write_text(raw_outline_path, merged_outline)
    _write_text(merged_outline_path, merged_outline)

    if not args.skip_human:
        print(f"Edit merged outline at: {merged_outline_path}")
        print("When done, press Enter to continue (or type 'abort' to stop).")
        if input().strip().lower() in {"abort", "quit", "exit", "q"}:
            print("Aborted by user.")
            return 1

    final_outline = merged_outline_path.read_text(encoding="utf-8")
    prompt = STAGE2_PROMPT.format(style=style, outline=final_outline)
    response = client.complete(
        prompt=prompt,
        max_tokens=args.stage2_max_tokens,
        temperature=args.temperature,
    )

    marp_markdown = response.get("content", "")
    presentation_path = out_dir / "presentation.md"
    _write_text(presentation_path, marp_markdown)
    print(f"Done. Output: {presentation_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
