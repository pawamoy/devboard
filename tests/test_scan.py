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

"""Tests for sharing repositories between board columns."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import TYPE_CHECKING

import pytest

from devboard import Board, Column, Devboard, Project
from devboard._internal import cache

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class AlternateProject(Project):
    """A separate project model that points to the same repositories."""


class FetchingBoard(Board):
    """Fetch projects during forced refreshes."""

    def force_refresh_item(self, item: object, /) -> None:
        """Fetch project data before scanning it."""
        if isinstance(item, Project):
            item.fetch_locked()


class FreshProjectsColumn(Column[Project]):
    HEADERS = ("Project",)

    def __init__(self, paths: list[Path], project_type: type[Project] = Project) -> None:
        """Initialize a column that creates its own project instances."""
        super().__init__()
        self.paths = paths
        self.project_type = project_type

    def list_items(self) -> Iterator[Project]:
        """Create fresh instances, as user boards normally do."""
        for path in self.paths:
            yield self.project_type(path)

    def populate_rows(self, project: Project) -> list[tuple[Project]]:
        """Show the project without running Git."""
        return [(project,)]


@pytest.mark.parametrize("background_tasks", [True, False], ids=["startup", "force-refresh"])
def test_repositories_shared_across_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    background_tasks: bool,
) -> None:
    """Share instances across columns and fetch each repository once, including aliases."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    alias = tmp_path / "alias"
    first.mkdir()
    second.mkdir()
    alias.symlink_to(first, target_is_directory=True)
    columns = [
        FreshProjectsColumn([first, second]),
        FreshProjectsColumn([alias, second], AlternateProject),
        FreshProjectsColumn([first]),
    ]
    fetched: list[Path] = []
    board = FetchingBoard(columns, force_refresh_on_startup=True)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)
    monkeypatch.setattr(Project, "fetch", lambda self: fetched.append(self.path.resolve()))
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=background_tasks)
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            if not background_tasks:
                app.force_refresh_board()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert Counter(fetched) == {first: 1, second: 1}
            assert [column.table.row_count for column in columns] == [2, 2, 1]
            assert len({id(row.data[0]) for column in columns for row in column.table.selectable_rows}) == 2
            for column in columns:
                for row in column.table.selectable_rows:
                    assert row.item is row.data[0]

    asyncio.run(run_test())


def test_board_bindings_choose_normal_or_forced_refresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A board decides which keys perform normal and forced refreshes."""
    repository = tmp_path / "repository"
    repository.mkdir()
    column = FreshProjectsColumn([repository])
    board = FetchingBoard(
        [column],
        bindings=[
            ("ctrl+r", "refresh", "Refresh"),
            ("ctrl+shift+r", "force_refresh", "Force refresh"),
        ],
    )
    fetched: list[Path] = []
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)
    monkeypatch.setattr(Project, "fetch", lambda self: fetched.append(self.path.resolve()))

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False)
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            await pilot.press("ctrl+r")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert fetched == []

            await pilot.press("ctrl+shift+r")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert fetched == [repository]

    asyncio.run(run_test())
