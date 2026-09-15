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


class ColumnApp(App[None]):
    def __init__(self) -> None:
        """Initialize the app with two populated columns."""
        super().__init__()
        self.column = CollapsibleColumn()
        self.other_column = CollapsibleColumn()

    def compose(self) -> ComposeResult:
        """Compose the test app."""
        yield self.column
        yield self.other_column


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
