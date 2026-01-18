from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GifItem:
    name: str
    path: str


def scan_gifs(gif_dir: str) -> list[GifItem]:
    p = Path(gif_dir)
    if not p.exists():
        return []

    items: list[GifItem] = []
    for child in sorted(p.iterdir(), key=lambda x: x.name.lower()):
        if not child.is_file():
            continue
        if child.suffix.lower() != ".gif":
            continue
        # Resolve symlinks and normalize for consistent API results
        items.append(GifItem(name=child.name, path=str(Path(os.path.realpath(child)))))
    return items


def clamp_index(idx: int, n: int) -> int:
    if n <= 0:
        return 0
    return idx % n
