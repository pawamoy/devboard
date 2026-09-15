# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2023, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from appdirs import user_cache_dir

_CACHE_DIR = Path(user_cache_dir("devboard"))
_CACHE_FORMAT = 2

_ITEM_KEY = "%item"
"""Marker key used to serialize references to a row's source item."""
_MISSING_ITEM = object()


@dataclass(frozen=True)
class _CachedRow:
    """A row and the source-item information needed to restore it."""

    item_key: Any
    item: Any
    cells: tuple[Any, ...]


def _cache_file(board: str) -> Path:
    digest = hashlib.md5(board.encode()).hexdigest()[:8]  # noqa: S324
    slug = re.sub(r"[^\w.-]+", "-", Path(board).stem) or "board"
    return _CACHE_DIR / f"{slug}-{digest}.json"


def _encode_cell(cell: Any, *, item: Any = _MISSING_ITEM) -> Any:
    """Convert a cell value to JSON-compatible data."""
    if item is not _MISSING_ITEM and cell is item:
        return {_ITEM_KEY: True}
    if cell is None or isinstance(cell, (str, int, float, bool)):
        return cell
    if isinstance(cell, (list, tuple)):
        return [_encode_cell(value, item=item) for value in cell]
    if isinstance(cell, dict) and all(isinstance(key, str) for key in cell):
        return {key: _encode_cell(value, item=item) for key, value in cell.items()}
    return str(cell)


def _encode_rows(rows: list[_CachedRow]) -> list[dict[str, Any]]:
    """Convert rows to JSON-compatible data."""
    return [
        {
            "item": _encode_cell(row.item_key),
            "cells": [_encode_cell(cell, item=row.item) for cell in row.cells],
        }
        for row in rows
    ]


def _decode_cell(cell: Any, item: Any) -> Any:
    """Restore references to a cached row's source item."""
    if isinstance(cell, dict) and cell == {_ITEM_KEY: True}:
        return item
    if isinstance(cell, list):
        return [_decode_cell(value, item) for value in cell]
    if isinstance(cell, dict):
        return {key: _decode_cell(value, item) for key, value in cell.items()}
    return cell


def _item_token(item_key: Any) -> str:
    """Convert an item key to a stable dictionary key."""
    return json.dumps(_encode_cell(item_key), ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _encoded_item_token(item_key: Any) -> str:
    """Convert an already encoded item key to a stable dictionary key."""
    return json.dumps(item_key, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _decode_rows(rows: list[dict[str, Any]], items: dict[str, Any]) -> list[tuple[Any, tuple[Any, ...]]]:
    """Restore cached rows and drop rows whose source item no longer exists."""
    decoded = []
    for row in rows:
        item = items.get(_encoded_item_token(row["item"]), _MISSING_ITEM)
        if item is _MISSING_ITEM:
            continue
        cells = tuple(_decode_cell(cell, item) for cell in row["cells"])
        decoded.append((item, cells))
    return decoded


def _save(board: str, data: dict[str, list[_CachedRow]], *, schema: list[list[str]] | None = None) -> None:
    file = _cache_file(board)
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = file.with_suffix(".json.tmp")
    tmp_file.write_text(
        json.dumps(
            {
                "format": _CACHE_FORMAT,
                "schema": schema,
                "rows": {key: _encode_rows(rows) for key, rows in data.items()},
            },
        ),
        encoding="utf8",
    )
    tmp_file.replace(file)


def _load(board: str, *, schema: list[list[str]] | None = None) -> dict[str, list[dict[str, Any]]] | None:
    try:
        cached = json.loads(_cache_file(board).read_text(encoding="utf8"))
    except (OSError, ValueError):
        return None
    if (
        not isinstance(cached, dict)
        or cached.get("format") != _CACHE_FORMAT
        or (schema is not None and cached.get("schema") != schema)
    ):
        return None
    rows = cached.get("rows")
    if not isinstance(rows, dict) or not all(
        isinstance(column_rows, list)
        and all(
            isinstance(row, dict)
            and set(row) == {"item", "cells"}
            and isinstance(row["cells"], list)
            for row in column_rows
        )
        for column_rows in rows.values()
    ):
        return None
    return rows
