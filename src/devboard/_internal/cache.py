from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from appdirs import user_cache_dir

from devboard._internal.projects import Project

_CACHE_DIR = Path(user_cache_dir("devboard"))

_PROJECT_KEY = "%project"
"""Marker key used to serialize project cells."""


def _cache_file(board: str) -> Path:
    digest = hashlib.md5(board.encode()).hexdigest()[:8]  # noqa: S324
    slug = re.sub(r"[^\w.-]+", "-", Path(board).stem) or "board"
    return _CACHE_DIR / f"{slug}-{digest}.json"


def _encode_rows(rows: list[tuple[Any, ...]]) -> list[list[Any]]:
    encoded = []
    for row in rows:
        cells: list[Any] = []
        for cell in row:
            if isinstance(cell, Project):
                cells.append({_PROJECT_KEY: str(cell.path)})
            elif cell is None or isinstance(cell, (str, int, float, bool)):
                cells.append(cell)
            else:
                cells.append(str(cell))
        encoded.append(cells)
    return encoded


def _decode_rows(rows: list[list[Any]], projects: dict[str, Project]) -> list[tuple[Any, ...]]:
    decoded = []
    for row in rows:
        cells: list[Any] = []
        for cell in row:
            if isinstance(cell, dict) and _PROJECT_KEY in cell:
                project = projects.get(cell[_PROJECT_KEY])
                if project is None:
                    break  # The project is gone: drop the row.
                cells.append(project)
            else:
                cells.append(cell)
        else:
            decoded.append(tuple(cells))
    return decoded


def _save(board: str, data: dict[str, list[tuple[Any, ...]]]) -> None:
    file = _cache_file(board)
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = file.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps({title: _encode_rows(rows) for title, rows in data.items()}))
    tmp_file.replace(file)


def _load(board: str) -> dict[str, list[list[Any]]] | None:
    try:
        return json.loads(_cache_file(board).read_text())
    except (OSError, ValueError):
        return None
