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

"""Tests for item refreshes requested by row actions."""

from __future__ import annotations

import asyncio
from threading import Event
from typing import TYPE_CHECKING, Any

import pytest

from devboard import Board, Column, Devboard, Row, row_action, rows_action
from devboard._internal import cache
from tests.test_items import CountingIssuesColumn, Issue, RefreshingBoard

if TYPE_CHECKING:
    from pathlib import Path


class UpdatedIssuesColumn(CountingIssuesColumn):
    """Show issues only after an action updates them."""

    def populate_rows(self, issue: Issue) -> list[tuple[Any, ...]]:
        """Record the scan and hide issues awaiting an update."""
        rows = super().populate_rows(issue)
        return rows if issue.title.startswith("Updated") else []


class UpdatingIssuesColumn(CountingIssuesColumn):
    """Update issues and request refreshes after removing their source rows."""

    targets: list[Column | type[Column]] | None = None
    force: bool = False

    @row_action
    def action_update(self, row: Row[Issue]) -> None:
        """Change an issue and refresh the columns affected by the change."""
        self._update_issue(row)

    @rows_action
    def action_update_batch(self, rows: list[Row[Issue]]) -> None:
        """Change all selected issues in one callback."""
        for row in rows:
            self._update_issue(row)

    def _update_issue(self, row: Row[Issue]) -> None:
        """Update an issue and request a refresh after removing its source row."""
        row.item.title = f"Updated {row.item.number}"
        row.remove()
        row.refresh(columns=self.targets, force=self.force)


@pytest.mark.parametrize("threaded", [True, False], ids=["background", "foreground"])
@pytest.mark.parametrize("scope", ["class", "instance", "all", "empty"])
@pytest.mark.parametrize("batch", [True, False], ids=["rows_action", "row_action"])
def test_action_refreshes_items_in_target_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    threaded: bool,
    scope: str,
    batch: bool,
) -> None:
    """Actions add missing target rows and preserve unrelated data and selections."""
    issues = [Issue("repo", 1, "First"), Issue("repo", 2, "Second"), Issue("repo", 3, "Updated existing")]
    source = UpdatingIssuesColumn(issues[:2])
    source.THREADED = threaded
    target = UpdatedIssuesColumn(issues)
    untouched = CountingIssuesColumn(issues)
    if scope == "class":
        source.targets = [UpdatedIssuesColumn]
    elif scope == "instance":
        source.targets = [target]
    elif scope == "empty":
        source.targets = []
    board = RefreshingBoard([source, target, untouched], bindings=[])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")

    async def run_test() -> None:
        app = Devboard(board="row-refresh")
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            source.scanned.clear()
            target.scanned.clear()
            untouched.scanned.clear()
            board.prepared.clear()
            target.table.current_row.select()
            for row in source.table.selectable_rows:
                row.select()

            # Both selected items need refreshes, even though neither has a target row yet.
            if batch:
                source.action_update_batch()
            else:
                source.action_update()
            await pilot.pause()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            expected_items = [] if scope == "empty" else [1, 2]
            assert sorted(target.scanned) == expected_items
            assert sorted(board.prepared) == [("normal", number) for number in expected_items]
            assert sorted(row.item.number for row in target.table.selected_rows) == [3]
            assert target.table.current_row.item.number == 3

            if scope == "all":
                assert sorted(source.scanned) == [1, 2]
                assert sorted(untouched.scanned) == [1, 2]
            else:
                assert source.table.row_count == 0
                assert source.scanned == []
                assert untouched.scanned == []
                assert [row.data for row in untouched.table.selectable_rows] == [
                    ["First"],
                    ["Second"],
                    ["Updated existing"],
                ]

            cached = cache._load("row-refresh")
            assert cached is not None
            assert sorted(row["cells"][0] for row in cached["1"]) == (
                ["Updated existing"] if scope == "empty" else ["Updated 1", "Updated 2", "Updated existing"]
            )

    asyncio.run(run_test())


def test_action_refresh_can_use_the_forced_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    """An action can request external preparation before refreshing a target."""
    issue = Issue("repo", 1, "First")
    source = UpdatingIssuesColumn([issue])
    target = UpdatedIssuesColumn([issue])
    source.targets = [target]
    source.force = True
    board = RefreshingBoard([source, target], bindings=[])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            board.prepared.clear()
            assert target.is_collapsed

            source.action_update()
            await pilot.pause()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert board.prepared == [("forced", 1)]
            assert target.table.current_row.data == ["Updated 1"]
            assert not target.is_collapsed

    asyncio.run(run_test())


def test_target_refresh_removes_items_no_longer_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A targeted refresh removes stale rows without changing other columns."""
    issue = Issue("repo", 1, "First")
    source = CountingIssuesColumn([issue])
    target = CountingIssuesColumn([issue])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([source, target]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            target.issues.clear()

            source.table.current_row.refresh(columns=[target])
            await pilot.pause()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert target.table.row_count == 0
            assert source.table.current_row.item is issue

    asyncio.run(run_test())


def test_action_refresh_waits_for_an_active_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refresh requests made during a scan are retained and run after it finishes."""
    issues = [Issue("repo", 1, "First"), Issue("repo", 2, "Second")]
    source = CountingIssuesColumn(issues)
    target = CountingIssuesColumn(issues)
    started = Event()
    release = Event()

    class BlockingBoard(Board):
        """Hold one scan open while rows request their next refresh."""

        blocking = False

        def refresh_item(self, item: Issue, /) -> None:
            """Block the first item until the test releases the scan."""
            if self.blocking and item.number == 1:
                started.set()
                assert release.wait(5)

    board = BlockingBoard([source, target])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)

    async def run_test() -> None:
        app = Devboard(background_tasks=False, workers=1)
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            snapshots = [row._for_worker() for row in source.table.selectable_rows]
            target.scanned.clear()
            board.blocking = True

            try:
                app.refresh_board()
                assert await asyncio.to_thread(started.wait, 5)

                for row in snapshots:
                    row.refresh(columns=[target])
                await pilot.pause()
            finally:
                release.set()

            async def wait_for_requested_scans() -> None:
                # New workers can start after wait_for_complete captures the active workers.
                while len(target.scanned) < 4:
                    await pilot.pause()

            await asyncio.wait_for(wait_for_requested_scans(), timeout=5)
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert target.scanned == [1, 2, 1, 2]
            assert [row.item.number for row in target.table.selectable_rows] == [1, 2]

    asyncio.run(run_test())
