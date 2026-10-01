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

"""Tests for filtering displayed rows without discarding board data."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from textual.command import CommandInput, CommandPalette
from textual.widgets import Input
from textual.widgets.data_table import DuplicateKey

from devboard import Board, Devboard, Row
from devboard._internal import cache
from devboard._internal.filtering import _FilterInput
from tests.test_items import Issue, IssuesColumn

if TYPE_CHECKING:
    from pathlib import Path


def test_filter_replaces_matches_and_preserves_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Changing and clearing filters restores row identity, order, and selection."""
    issues = [Issue("org/alpha", 1, "Alpha"), Issue("org/beta", 2, "Beta"), Issue("org/alpha", 3, "Gamma")]
    column = IssuesColumn(issues)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            rows = list(column.table.selectable_rows)
            rows[1].select()
            rows[2].select()
            column.table.move_cursor(row=2)

            # Hide a selected row and retain the cursor on a matching row.
            column.filter_rows(lambda row: row.item.repository == "org/alpha")

            assert [row.item.number for row in column.table.selectable_rows] == [1, 3]
            assert column.table.current_row.key == rows[2].key
            assert [row.item.number for row in column.table.selected_rows] == [3]
            column.action_record()
            assert column.applied == [issues[2]]

            # A replacement filter can find rows hidden by the previous filter.
            column.filter_rows(lambda row: row.item.repository == "org/beta")

            assert column.table.current_row.item is issues[1]
            assert column.table.current_row.selected

            column.filter_rows(None)
            await pilot.pause()

            assert [row.key for row in column.table.selectable_rows] == [row.key for row in rows]
            assert [row.item.number for row in column.table.selected_rows] == [2, 3]

    asyncio.run(run_test())


def test_filter_text_targets_specific_or_all_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default matching ignores case, and clearing can target individual columns."""
    issues = [Issue("repo", 1, "Alpha"), Issue("repo", 2, "Beta")]
    first = IssuesColumn(issues)
    second = IssuesColumn(issues)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([first, second]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test():
            await app.workers.wait_for_complete()

            app.filter_rows("ALPHA", [first])

            assert first.table.row_count == 1
            assert second.table.row_count == 2

            app.filter_rows("beta")

            assert first.table.current_row.item is issues[1]
            assert second.table.current_row.item is issues[1]

            app.filter_rows("", [first])

            assert first.table.row_count == 2
            assert second.table.row_count == 1

            app.filter_rows(None)

            assert second.table.row_count == 2

    asyncio.run(run_test())


def test_board_hook_filters_source_items_and_survives_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """A repository filter keeps matching new rows across normal and forced scans."""

    class BacklogBoard(Board):
        def matches_filter(self, row: Row[Issue], value: str, /) -> bool:
            """Select one repository without inspecting display cells."""
            return row.item.repository == value

    issues = [Issue("org/alpha", 1, "First"), Issue("org/beta", 2, "Second")]
    column = IssuesColumn(issues)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: BacklogBoard([column]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test():
            await app.workers.wait_for_complete()
            app.filter_rows("org/alpha")
            issues.extend([Issue("org/alpha", 3, "Third"), Issue("org/beta", 4, "Fourth")])

            app.refresh_board()
            await app.workers.wait_for_complete()

            assert [row.item.number for row in column.table.selectable_rows] == [1, 3]

            app.force_refresh_board()
            await app.workers.wait_for_complete()
            app.filter_rows(None)

            assert {row.item.number for row in column.table.selectable_rows} == {1, 2, 3, 4}

    asyncio.run(run_test())


def test_item_refresh_retains_hidden_rows_and_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refreshing a visible item preserves hidden items and their selections."""
    issues = [Issue("repo", 1, "Alpha"), Issue("repo", 2, "Beta")]
    column = IssuesColumn(issues)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test():
            await app.workers.wait_for_complete()
            next(row for row in column.table.selectable_rows if row.item.number == 2).select()
            app.filter_rows("Alpha")
            app.set_focus(column.table)
            issues[0].title = "Alpha updated"

            app.action_refresh_item()
            await app.workers.wait_for_complete()

            assert column.table.current_row.data == ["Alpha updated"]
            assert column.table.row_count == 1

            app.filter_rows(None)

            assert [row.item.number for row in column.table.selected_rows] == [2]
            assert [row.data for row in column.table.selectable_rows] == [["Alpha updated"], ["Beta"]]

    asyncio.run(run_test())


def test_hidden_rows_are_cached_and_removed_rows_stay_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Saving a filtered board retains hidden rows and excludes deleted rows."""
    issues = [Issue("repo", 1, "Alpha"), Issue("repo", 2, "Beta")]
    column = IssuesColumn(issues)
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(board="filter-cache")
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            removed_row = column.table.current_row._for_worker()
            app.filter_rows("Beta")
            app._update_cache()

            cached = cache._load("filter-cache")
            assert cached is not None
            assert len(cached["0"]) == 2

            # A background action can finish after its row becomes hidden.
            removed_row.remove()
            await pilot.pause()
            app._update_cache()
            app.filter_rows(None)

            assert column.table.current_row.item is issues[1]
            cached = cache._load("filter-cache")
            assert cached is not None
            assert len(cached["0"]) == 1

    asyncio.run(run_test())


def test_filtering_to_no_rows_collapses_and_clearing_expands(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty filtered column expands again when its rows become visible."""
    column = IssuesColumn([Issue("repo", 1, "Alpha")])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()
            app.set_focus(column.table)

            app.filter_rows("no match")
            await pilot.pause()

            assert column.table.row_count == 0
            assert column.is_collapsed
            assert app.focused is column
            column.action_record()
            assert column.applied == []

            app.filter_rows(None)
            await pilot.pause()

            assert column.table.row_count == 1
            assert not column.is_collapsed
            assert app.focused is column.table

    asyncio.run(run_test())


def test_filter_retains_explicit_keys_and_sorts_hidden_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sorting and adding rows while filtered also update the retained rows."""
    column = IssuesColumn([])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test():
            await app.workers.wait_for_complete()
            first_key = column.table.add_row("Beta", key="first")
            column.table.add_row("Alpha", key="second")
            column.filter_rows(lambda row: "Beta" in row.data)

            with pytest.raises(DuplicateKey):
                column.table.add_row("Duplicate", key="second")

            column.table.add_row("Gamma", key="third")
            column.table.sort("title", reverse=True)
            column.filter_rows(None)

            assert [column.table.get_row(row.key)[1:] for row in column.table.ordered_rows] == [
                ["Gamma"],
                ["Beta"],
                ["Alpha"],
            ]
            assert column.table.get_row(first_key)[1:] == ["Beta"]

    asyncio.run(run_test())


@pytest.mark.parametrize("board_filter_key", ["ctrl+p", "ctrl+f"])
def test_filter_commands_and_default_binding_target_their_scopes(
    monkeypatch: pytest.MonkeyPatch,
    board_filter_key: str,
) -> None:
    """The palette and default shortcut submit, clear, and cancel filters in their chosen scopes."""
    issues = [Issue("repo", 1, "Alpha"), Issue("repo", 2, "Beta")]
    first = IssuesColumn(issues)
    second = IssuesColumn(issues)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([first, second]))

    async def run_test() -> None:
        app = Devboard(background_tasks=False)
        async with app.run_test() as pilot:
            await app.workers.wait_for_complete()

            await pilot.press(board_filter_key)
            if board_filter_key == "ctrl+p":
                assert isinstance(app.screen, CommandPalette)
                app.screen.query_one(CommandInput).value = "Filter board"
                await pilot.pause()
                await app.workers.wait_for_complete()
                await pilot.press("enter")

            assert isinstance(app.screen, _FilterInput)
            app.screen.query_one(Input).value = "Alpha"
            await pilot.press("enter")

            assert first.table.row_count == 1
            assert second.table.row_count == 1

            # Column filtering replaces the board filter only in the focused column.
            app.set_focus(second.table)
            await pilot.press("ctrl+p")
            app.screen.query_one(CommandInput).value = "Filter column"
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.press("enter")

            assert isinstance(app.screen, _FilterInput)
            assert app.screen.query_one(Input).value == "Alpha"
            app.screen.query_one(Input).value = "Beta"
            await pilot.press("enter")

            assert first.table.current_row.item is issues[0]
            assert second.table.current_row.item is issues[1]

            # Cancel retains the active filter; submitting empty text clears it.
            app.set_focus(second.table)
            app.action_filter_column()
            await pilot.pause()
            app.screen.query_one(Input).value = "Alpha"
            await pilot.press("escape")

            assert second.table.current_row.item is issues[1]

            app.action_filter_column()
            await pilot.pause()
            assert app.screen.query_one(Input).value == "Beta"
            app.screen.query_one(Input).value = ""
            await pilot.press("enter")

            assert first.table.row_count == 1
            assert second.table.row_count == 2

    asyncio.run(run_test())
