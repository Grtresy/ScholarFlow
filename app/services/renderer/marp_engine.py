"""Thin wrapper around Marp CLI rendering."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


def render_marp(input_md: Path, output_path: Path, theme: Optional[Path] = None) -> None:
    """Render Markdown to PPTX/PDF via Marp CLI."""
    cmd = ["marp", str(input_md), "--output", str(output_path)]
    if theme:
        cmd.extend(["--theme", str(theme)])
    subprocess.run(cmd, check=True)
