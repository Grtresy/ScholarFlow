"""Pydantic/DTO models placeholder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Chunk:
    id: int
    title: str
    text: str


@dataclass
class OutlineItem:
    chunk_id: int
    outline: str
    chunk_title: str | None = None


@dataclass
class OutlineMergeResult:
    outline_merged: str
