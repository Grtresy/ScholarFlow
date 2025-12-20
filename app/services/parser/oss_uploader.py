"""Upload images to object storage."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


def upload_images(paths: Iterable[Path]) -> List[str]:
    """Upload local image files and return remote URLs.

    Placeholder: implement provider-specific logic (e.g., OSS, S3).
    """
    raise NotImplementedError("Implement OSS upload logic")
