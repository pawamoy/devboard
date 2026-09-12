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
from typing import TYPE_CHECKING, Any

import pytest

from devboard import Column, Devboard, Project
from devboard._internal import cache

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class CacheColumn(Column):
    TITLE = "Results"
    HEADERS = ("Project", "Value")

    def __init__(self, path: Path) -> None:
        """Initialize a column with a project backed by a text file."""
        super().__init__()
        self.project = Project(path)

    def list_projects(self) -> Iterator[Project]:
        """Return the column's project."""
        yield self.project

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Any, ...]]:
        """Read the current value without invoking Git."""
        value = project.path.read_text(encoding="utf-8")
        return [(project, value)] if value else []


@pytest.fixture(name="cached_board")
def _fixture_cached_board(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("first", "second"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(
        Devboard,
        "_load_columns",
        lambda self: [CacheColumn(tmp_path / name) for name in ("first", "second")],
    )
    monkeypatch.setattr(Devboard, "_fetch_projects", lambda self, projects: None)
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
                    "0": [[{"%project": str(cached_board / "first")}, value]],
                    "1": [[{"%project": str(cached_board / "second")}, "second"]],
                }

    asyncio.run(run_test())


@pytest.mark.parametrize("value", ["updated", ""])
def test_column_update_preserves_other_cached_columns(cached_board: Path, value: str) -> None:
    """Updating a later column preserves board indices and records empty results."""

    async def run_test() -> None:
        app = Devboard(board="test-board")
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            (cached_board / "second").write_text(value, encoding="utf-8")
            list(app.query(Column))[1].update()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert cache._load("test-board") == {
                "0": [[{"%project": str(cached_board / "first")}, "first"]],
                "1": [[{"%project": str(cached_board / "second")}, value]] if value else [],
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
