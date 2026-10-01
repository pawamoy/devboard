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

"""Tests for column interactions."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from textual.app import App
from textual.widgets import Static

from devboard import Column

if TYPE_CHECKING:
    from textual.app import ComposeResult


class CollapsibleColumn(Column):
    TITLE = "Results"
    HEADERS = ("Project",)

    def on_mount(self) -> None:
        """Populate the column with one row."""
        self._reset()
        self._extend([("devboard",)])
        self._finalize()


class EmptyColumn(Column):
    TITLE = "Empty"
    HEADERS = ("Project",)

    def on_mount(self) -> None:
        """Finish initial population without adding rows."""
        self._reset()
        self._finalize()


class ColumnApp(App[None]):
    def __init__(self, column: Column | None = None) -> None:
        """Initialize the app with a configurable first column and two populated columns."""
        super().__init__()
        self.column = column if column is not None else CollapsibleColumn()
        self.other_column = CollapsibleColumn()
        self.third_column = CollapsibleColumn()

    def compose(self) -> ComposeResult:
        """Compose the test app."""
        yield self.column
        yield self.other_column
        yield self.third_column


def test_removing_last_row_collapses_and_keeps_column_focusable() -> None:
    """A truly empty column remains reachable and can be expanded again."""

    async def run_test() -> None:
        app = ColumnApp()
        async with app.run_test() as pilot:
            column = app.column
            app.set_focus(column.table)

            column.table.current_row.remove()
            await pilot.pause()

            assert column.table.row_count == 0
            assert column.is_collapsed is True
            assert column.can_focus is True
            assert column in app.screen.focus_chain
            assert column.table not in app.screen.focus_chain
            assert app.focused is column

            await pilot.press("tab")

            assert app.focused is app.other_column.table

            await pilot.press("shift+tab", "c")
            await pilot.pause()

            assert not column.is_collapsed
            assert app.focused is column.table
            assert column.table in app.screen.focus_chain

    asyncio.run(run_test())


@pytest.mark.parametrize("collapsed_state", ["empty", "filtered", "manual", "maximized"])
def test_collapsed_columns_support_click_tab_expand_and_maximize(collapsed_state: str) -> None:
    """Collapsed columns support the same interactions regardless of why they collapsed."""

    async def run_test() -> None:
        app = ColumnApp(EmptyColumn() if collapsed_state == "empty" else None)
        async with app.run_test() as pilot:
            column = app.column
            if collapsed_state == "filtered":
                column.filter_rows(lambda row: False)
            elif collapsed_state == "manual":
                column._collapse()
            elif collapsed_state == "maximized":
                app.other_column.action_toggle_maximize()
            await pilot.pause()

            assert column.is_collapsed
            visible_rows = column.table.row_count

            # Tab navigation and clicking both reach the collapsed column.
            app.set_focus(app.other_column.table)
            await pilot.press("shift+tab")

            assert app.focused is column

            await pilot.press("tab")

            assert app.focused is app.other_column.table

            await pilot.click(column.query_one(".column-title", Static))

            assert app.focused is column

            # Expansion focuses the table even when it has no visible rows.
            await pilot.press("c")
            await pilot.pause()

            assert not column.is_collapsed
            assert app.focused is column.table
            assert column.table in app.screen.focus_chain
            assert column.table.row_count == visible_rows

            # Maximizing a collapsed column leaves the other collapsed columns reachable.
            await pilot.press("c", "m")
            await pilot.pause()

            assert not column.is_collapsed
            assert app.focused is column.table
            for other in (app.other_column, app.third_column):
                assert other.is_collapsed
                assert other in app.screen.focus_chain

            await pilot.press("m")
            await pilot.pause()

            assert column.is_collapsed
            assert app.focused is column
            assert column.table.row_count == visible_rows

    asyncio.run(run_test())


def test_c_key_collapses_and_expands_focused_column() -> None:
    """The C key toggles a populated column between its full and compact layouts."""

    async def run_test() -> None:
        app = ColumnApp()
        async with app.run_test() as pilot:
            column = app.column

            assert column.table.row_count == 1
            assert column.table.styles.display == "block"

            await pilot.press("c")
            await pilot.pause()

            assert column.region.width == 3
            assert column.table.styles.display == "none"
            assert str(column.query_one(".column-title", Static).content) == "▼ Results"
            assert app.focused is column

            await pilot.press("tab")
            await pilot.pause()

            assert app.focused is app.other_column.table

            await pilot.press("shift+tab")
            await pilot.pause()

            assert app.focused is column

            await pilot.press("c")
            await pilot.pause()

            assert column.region.width > 3
            assert column.table.styles.display == "block"
            assert str(column.query_one(".column-title", Static).content) == "▶ Results"
            assert app.focused is column.table

    asyncio.run(run_test())


def test_m_key_maximizes_column_and_restores_previous_layout() -> None:
    """The M key expands the focused column and restores every column when pressed again."""

    async def run_test() -> None:
        app = ColumnApp()
        async with app.run_test() as pilot:
            # Start with one user-collapsed column between two expanded columns.
            app.other_column._collapse()

            await pilot.press("m")
            await pilot.pause()

            # Maximizing keeps the current column open and collapses every other column.
            assert app.column.is_collapsed is False
            assert app.other_column.is_collapsed is True
            assert app.third_column.is_collapsed is True
            assert app.focused is app.column.table

            await pilot.press("m")
            await pilot.pause()

            # Unmaximizing restores the exact expanded and collapsed layout.
            assert app.column.is_collapsed is False
            assert app.other_column.is_collapsed is True
            assert app.other_column.can_focus is True
            assert app.third_column.is_collapsed is False
            assert app.focused is app.column.table

    asyncio.run(run_test())


def test_m_key_restores_maximized_column_to_collapsed_state() -> None:
    """Unmaximizing re-collapses a column that was collapsed before maximizing."""

    async def run_test() -> None:
        app = ColumnApp()
        async with app.run_test() as pilot:
            await pilot.press("c")
            await pilot.pause()

            await pilot.press("m")
            await pilot.pause()

            assert app.column.is_collapsed is False
            assert app.focused is app.column.table

            await pilot.press("m")
            await pilot.pause()

            assert app.column.is_collapsed is True
            assert app.column.can_focus is True
            assert app.other_column.is_collapsed is False
            assert app.third_column.is_collapsed is False
            assert app.focused is app.column

    asyncio.run(run_test())
