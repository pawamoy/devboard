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

"""Tests for caching recomputed board data."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from devboard import Board, Column, Devboard, Project
from devboard._internal import cache

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path


class CacheColumn(Column[Project]):
    TITLE = "Results"
    HEADERS: tuple[str, ...] = ("Project", "Value")

    def __init__(self, path: Path) -> None:
        """Initialize a column with a project backed by a text file."""
        super().__init__()
        self.project = Project(path)

    def list_items(self) -> Iterator[Project]:
        """Return the column's project."""
        yield self.project

    def populate_rows(self, project: Project) -> list[tuple[Any, ...]]:
        """Read the current value without invoking Git."""
        value = project.path.read_text(encoding="utf-8")
        return [(project, value)] if value else []


class OtherCacheColumn(CacheColumn):
    """A different column type with the same headers."""


class WrappedCacheColumn(CacheColumn):
    """A column with an explicit cache representation for text values."""

    def __init__(self, path: Path) -> None:
        """Initialize the column and its restoration log."""
        super().__init__(path)
        self.restored: list[str] = []

    def serialize_cell(self, value: Any) -> Any:
        """Wrap text so the cache format differs from the display format."""
        if isinstance(value, str):
            return {"text": value}
        return value

    def deserialize_cell(self, value: Any) -> Any:
        """Restore wrapped text and record that the hook ran."""
        if isinstance(value, dict) and set(value) == {"text"}:
            text = value["text"]
            self.restored.append(text)
            return text
        return value


def _cache_board(columns: Sequence[CacheColumn]) -> Board:
    """Create a cache test board with a normal refresh binding."""
    return Board(columns, bindings=[("f5, ctrl+r", "refresh", "Refresh")])


@pytest.fixture(name="cached_board")
def _fixture_cached_board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("first", "second"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(
        Devboard,
        "_load_board",
        lambda self: _cache_board([CacheColumn(tmp_path / name) for name in ("first", "second")]),
    )
    return tmp_path


@pytest.mark.parametrize("refresh_key", ["f5", "ctrl+r"])
def test_refresh_saves_latest_results(cached_board: Path, refresh_key: str) -> None:
    """Every full refresh replaces the startup snapshot on disk."""

    async def run_test() -> None:
        app = Devboard(board="test-board")
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            for value in ("refreshed", "refreshed again"):
                (cached_board / "first").write_text(value, encoding="utf-8")
                await pilot.press(refresh_key)
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

                assert app.query_one(Column).table.current_row.data[1] == value
                assert cache._load("test-board") == {
                    "0": [
                        {
                            "item": str(cached_board / "first"),
                            "cells": [{"%item": True}, value],
                        },
                    ],
                    "1": [
                        {
                            "item": str(cached_board / "second"),
                            "cells": [{"%item": True}, "second"],
                        },
                    ],
                }

    asyncio.run(run_test())


@pytest.mark.parametrize("value", ["updated", ""])
def test_column_update_preserves_other_cached_columns(cached_board: Path, value: str) -> None:
    """Updating a later column preserves board indices and records empty results."""

    async def run_test() -> None:
        app = Devboard(board="test-board")
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            (cached_board / "second").write_text(value, encoding="utf-8")
            list(app.query(Column))[1].update()
            await pilot.pause()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert cache._load("test-board") == {
                "0": [
                    {
                        "item": str(cached_board / "first"),
                        "cells": [{"%item": True}, "first"],
                    },
                ],
                "1": [
                    {
                        "item": str(cached_board / "second"),
                        "cells": [{"%item": True}, value],
                    },
                ]
                if value
                else [],
            }

    asyncio.run(run_test())


def test_disabled_background_tasks_leave_cache_untouched(cached_board: Path) -> None:
    """Screenshots and tests with background tasks disabled do not update the cache."""
    cache._save("test-board", {"0": [], "1": []})

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False)
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            (cached_board / "first").write_text("refreshed", encoding="utf-8")
            await pilot.press("f5")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert app.query_one(Column).table.current_row.data[1] == "refreshed"
            assert cache._load("test-board") == {"0": [], "1": []}

    asyncio.run(run_test())


@pytest.mark.parametrize("change", ["unchanged", "reorder", "headers", "title", "type", "version", "rows"])
def test_cache_matches_board_layout(cached_board: Path, monkeypatch: pytest.MonkeyPatch, change: str) -> None:
    """Reuse compatible snapshots and invalidate them when columns change."""

    def make_columns() -> list[CacheColumn]:
        columns = [CacheColumn(cached_board / name) for name in ("first", "second")]
        columns[0].TITLE = "First"
        columns[0].HEADERS = ("Project", "Value", "Extra")
        columns[1].TITLE = "Second"
        return columns

    async def run_test() -> None:
        monkeypatch.setattr(Devboard, "_load_board", lambda self: _cache_board(make_columns()))
        previous_app = Devboard(board="test-board")
        async with previous_app.run_test():
            await asyncio.wait_for(previous_app.workers.wait_for_complete(), timeout=5)

        if change == "rows":
            file = cache._cache_file("test-board")
            payload = json.loads(file.read_text(encoding="utf-8"))
            payload["rows"]["0"][0]["cells"].append("unexpected cell")
            file.write_text(json.dumps(payload), encoding="utf-8")

        columns = make_columns()
        if change == "reorder":
            columns.reverse()
        elif change == "headers":
            columns[0].HEADERS = ("Project", "Value")
        elif change == "title":
            columns[0].TITLE = "Renamed"
        elif change == "type":
            replacement = OtherCacheColumn(cached_board / "first")
            replacement.TITLE = columns[0].TITLE
            replacement.HEADERS = columns[0].HEADERS
            columns[0] = replacement
        elif change == "version":
            columns[0].CACHE_VERSION += 1
        monkeypatch.setattr(Devboard, "_load_board", lambda self: _cache_board(columns))
        app = Devboard(board="test-board")
        show_cached = Mock(wraps=app._show_cached_columns)
        monkeypatch.setattr(app, "_show_cached_columns", show_cached)
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert show_cached.call_count == (1 if change == "unchanged" else 0)
            for column in columns:
                assert column.table.current_row.data[1] == column.project.path.name

    asyncio.run(run_test())


def test_nested_cache_values_restore_source_items(tmp_path: Path) -> None:
    """Cache encoding preserves nested data and restores source-item references."""
    project = Project(tmp_path / "project")
    rows = [
        cache._CachedRow(
            item_key=project.devboard_key,
            item=project,
            cells=({"owner": project, "labels": ["ready", project]},),
        ),
    ]

    encoded = cache._encode_rows(rows)
    decoded = cache._decode_rows(encoded, {cache._item_token(project.devboard_key): project})

    assert encoded == [
        {
            "item": str(project.path),
            "cells": [
                {
                    "owner": {"%item": True},
                    "labels": ["ready", {"%item": True}],
                },
            ],
        },
    ]
    assert decoded == [(project, ({"owner": project, "labels": ["ready", project]},))]


def test_column_cache_serialization_hooks(cached_board: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Columns can define a stable cache representation for custom cells."""

    def make_columns() -> list[WrappedCacheColumn]:
        return [WrappedCacheColumn(cached_board / name) for name in ("first", "second")]

    async def run_test() -> None:
        monkeypatch.setattr(Devboard, "_load_board", lambda self: _cache_board(make_columns()))
        previous_app = Devboard(board="test-board")
        async with previous_app.run_test():
            await asyncio.wait_for(previous_app.workers.wait_for_complete(), timeout=5)

        cached = cache._load("test-board")
        assert cached is not None
        assert cached["0"][0]["cells"][1] == {"text": "first"}

        columns = make_columns()
        monkeypatch.setattr(Devboard, "_load_board", lambda self: _cache_board(columns))
        app = Devboard(board="test-board")
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

        assert columns[0].restored == ["first"]
        assert columns[1].restored == ["second"]

    asyncio.run(run_test())


def test_legacy_cache_is_ignored(cached_board: Path) -> None:
    """Old position-only caches cannot safely identify their columns."""
    file = cache._cache_file("test-board")
    file.parent.mkdir(parents=True)
    file.write_text(
        json.dumps({"0": [[{"%project": str(cached_board / "first")}, "template", "old", "latest"]], "1": []}),
        encoding="utf-8",
    )

    async def run_test() -> None:
        app = Devboard(board="test-board")
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            assert app.query_one(Column).table.current_row.data[1] == "first"

    asyncio.run(run_test())
