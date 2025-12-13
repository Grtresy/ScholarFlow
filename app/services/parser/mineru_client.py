"""Client wrapper for invoking MinerU parsing."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Tuple


def parse_pdf(pdf_path: Path) -> Tuple[str, list[str]]:
    """Parse PDF via MinerU; returns markdown text and list of image paths.

    Placeholder implementation to be replaced with actual MinerU integration.
    """
    raise NotImplementedError("Integrate MinerU service or CLI here")
