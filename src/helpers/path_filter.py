"""Glob filtering for batch import / palette tools."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def normalize_name_pattern(pattern: str) -> str | None:
    """Return a usable glob pattern, or None when filtering is disabled."""
    cleaned = (pattern or "").strip()
    if not cleaned or cleaned == "*":
        return None
    return cleaned


def matches_name_pattern(name: str, pattern: str | None) -> bool:
    if pattern is None:
        return True
    return fnmatch.fnmatch(name.lower(), pattern.lower())


def filter_by_name_pattern(
    items: list[T],
    pattern: str,
    *,
    key: Callable[[T], str],
) -> tuple[list[T], int]:
    """Keep items whose key matches pattern; return (kept, filtered_out_count)."""
    normalized = normalize_name_pattern(pattern)
    if normalized is None:
        return items, 0
    kept = [item for item in items if matches_name_pattern(key(item), normalized)]
    return kept, len(items) - len(kept)
