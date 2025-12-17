"""Interactive real-data HIL test runner for ScholarFlow.

This script runs the end-to-end PDF→PPTX workflow on a real PDF and
performs Human-In-the-Loop (HIL) interaction via the terminal.

Default input: tests/inputs/test.pdf
Default output: data/outputs/{task_id}/presentation.pptx

Usage (interactive):
  python tests/test_real_pdf_hil.py
  python tests/test_real_pdf_hil.py --pdf tests/inputs/test.pdf --style academic --format pptx

Environment requirements:
  - MINERU_API_KEY        (required for PDF parsing)
  - LLM_API_KEY (or OPENAI_API_KEY / DEEPSEEK_API_KEY)
  - npm install (to get @marp-team/marp-cli in node_modules/.bin/marp)
  - Chromium/Chrome installed (marp-engine requires a CHROME_PATH)
"""

from __future__ import annotations

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.graph.state import (
    PresentationStyle,
    TaskStatus,
    create_initial_state,
)
from app.graph.workflow import run_workflow, resume_workflow


def _gen_task_id(prefix: str = "real") -> str:
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{now}"


def _print_state_summary(state: Dict[str, Any]) -> None:
    status = state.get("status")
    step = state.get("current_step", "")
    prog = state.get("progress_percentage", 0.0)
    print(f"\n[STATE] status={status}, progress={prog:.1f}%, step={step}")


def _print_review_points(state: Dict[str, Any]) -> None:
    rps = state.get("review_points", []) or []
    if not rps:
        print("\n[HIL] 没有待审核点（review_points 为空）。")
        return
    print("\n[HIL] 待审核点：")
    for i, rp in enumerate(rps, 1):
        rtype = rp.get("type", "unknown")
        node = rp.get("node", "?")
        prompt = rp.get("prompt", "")
        content = (rp.get("content", "") or "").strip()
        preview = content[:500] + ("..." if len(content) > 500 else "")
        print(f"-- #{i} type={rtype} node={node}")
        if prompt:
            print(f"   prompt: {prompt}")
        print("   content preview:")
        for line in preview.splitlines():
            print(f"     {line}")

    outline_path = state.get("merged_outline_path")
    if outline_path:
        print(f"\n[HIL] 合并大纲文件: {outline_path}")


def _prompt_feedback() -> Dict[str, Any]:
    print("\n[HIL] 请选择操作：")
    print("  y = 批准通过 (approved)")
    print("  r = 要求重新生成 (regenerate)")
    print("  a = 终止任务 (abort)")
    while True:
        choice = input("你的选择 [y/r/a]: ").strip().lower()
        if choice in {"y", "r", "a"}:
            break
        print("请输入 y / r / a")

    comments = input("可选备注（直接回车跳过）：").strip()

    if choice == "y":
        return {"approved": True, "action": None, "comments": comments}
    if choice == "r":
        return {"approved": False, "action": "regenerate", "comments": comments}
    return {"approved": False, "action": "abort", "comments": comments}


async def _run_once(initial_state: Dict[str, Any], thread_id: str) -> Dict[str, Any]:
    state = await run_workflow(initial_state, thread_id=thread_id)
    _print_state_summary(state)
    return state


async def _resume_loop(task_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Resume workflow with terminal HIL until completed/failed."""
    while True:
        status = state.get("status")
        needs_hil = state.get("needs_human_review", False)

        if status in (TaskStatus.HUMAN_REVIEW.value, TaskStatus.PAUSED.value) or needs_hil:
            _print_review_points(state)
            feedback = _prompt_feedback()
            print("\n[HIL] 提交反馈并恢复工作流…")
            state = await resume_workflow(task_id, feedback)
            _print_state_summary(state)
            continue

        # Non-HIL states
        if status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
            return state

        # Other in-progress states (e.g., rendering)
        # Resume without feedback (continue processing)
        print("\n[INFO] 工作流继续执行中（无需人工输入）…")
        state = await resume_workflow(task_id, None)
        _print_state_summary(state)


async def main_async(args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists():
        print(f"[ERROR] PDF 不存在: {pdf_path}")
        return 2

    # Validate style
    try:
        style = PresentationStyle(args.style)
    except ValueError:
        print(f"[ERROR] 非法风格: {args.style}. 可选: academic/popular/business")
        return 2

    task_id = args.task_id or _gen_task_id()
    print(f"[RUN] task_id={task_id}")
    print(f"[RUN] 输入PDF: {pdf_path}")
    print(f"[RUN] 风格: {style.value}，输出格式: {args.format}")

    initial_state = create_initial_state(
        task_id=task_id,
        pdf_path=str(pdf_path),
        presentation_style=style.value,
        max_chars=args.max_chars,
        target_chunks=args.target_chunks,
        output_format=args.format,
        enable_human_review=True,
    )

    print("\n[STEP] 启动工作流（首次运行）…")
    state = await _run_once(initial_state, thread_id=task_id)

    print("\n[STEP] 进入交互式 HIL 循环…")
    state = await _resume_loop(task_id, state)

    status = state.get("status")
    if status == TaskStatus.COMPLETED.value:
        out = state.get("output_path")
        if out:
            out_path = Path(out)
            exists = out_path.exists()
            print(f"\n[SUCCESS] 演示文稿生成完成: {out}")
            print(f"[CHECK] 文件存在: {exists}")
            return 0
        print("\n[WARN] 状态完成但未返回 output_path。")
        return 0

    print(f"\n[FAIL] 工作流失败: {state.get('error_message', '未知错误')}\n")
    return 1


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run real-data HIL test for ScholarFlow")
    p.add_argument("--pdf", default=str(Path("tests/inputs/第13周作业题.pdf").resolve()), help="Path to input PDF")
    p.add_argument("--style", default="academic", help="Presentation style: academic/popular/business")
    p.add_argument("--format", default="pptx", help="Output format: pptx/pdf/html")
    p.add_argument("--max-chars", type=int, default=6000, help="Maximum characters per chunk")
    p.add_argument("--target-chunks", type=int, default=6, help="Target number of chunks")
    p.add_argument("--task-id", default=None, help="Optional custom task id")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    try:
        code = asyncio.run(main_async(args))
        sys.exit(code)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] 用户中断。")
        sys.exit(130)


if __name__ == "__main__":
    main()
