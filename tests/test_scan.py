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

from devboard import Column, Devboard, Project
from devboard._internal import cache

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class FreshProjectsColumn(Column):
    HEADERS = ("Project",)

    def __init__(self, paths: list[Path]) -> None:
        """Initialize a column that creates its own project instances."""
        super().__init__()
        self.paths = paths

    def list_projects(self) -> Iterator[Project]:
        """Create fresh instances, as user boards normally do."""
        for path in self.paths:
            yield Project(path)

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Project]]:
        """Show the project without running Git."""
        return [(project,)]


@pytest.mark.parametrize("background_tasks", [True, False], ids=["startup", "fetch-all"])
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
        FreshProjectsColumn([alias, second]),
        FreshProjectsColumn([first]),
    ]
    fetched: list[Path] = []
    monkeypatch.setattr(Devboard, "_load_columns", lambda self: columns)
    monkeypatch.setattr(Project, "fetch", lambda self: fetched.append(self.path.resolve()))
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=background_tasks)
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            if not background_tasks:
                app.fetch_all()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert Counter(fetched) == {first: 1, second: 1}
            assert [column.table.row_count for column in columns] == [2, 2, 1]
            assert len({id(row.data[0]) for column in columns for row in column.table.selectable_rows}) == 2

    asyncio.run(run_test())
