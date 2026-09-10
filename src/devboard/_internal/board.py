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

from functools import partial
from typing import TYPE_CHECKING, Any, cast

from textual.containers import Container
from textual.widgets import Static

from devboard._internal.datatable import SelectableRow, SelectableRowsDataTable
from devboard._internal.modal import ModalMixin
from devboard._internal.notifications import NotifyMixin
from devboard._internal.projects import Project

if TYPE_CHECKING:
    from collections.abc import Iterable

    from textual.app import ComposeResult


class Row(SelectableRow):
    """A Devboard row."""

    @property
    def project(self) -> Project:
        """Devboard project."""
        for val in self.data:
            if isinstance(val, Project):
                return val
        raise ValueError("No project in row data")


class DataTable(SelectableRowsDataTable):
    """A Devboard data table."""

    ROW = Row
    """The class to instantiate rows."""


class Column(Container, ModalMixin, NotifyMixin):
    """A Devboard column."""

    TITLE: str = ""
    """The title of the column."""
    HEADERS: tuple[str, ...] = ()
    """The data table headers."""
    THREADED: bool = True
    """Whether actions of this column should run in the background."""
    DEFAULT_CLASSES = "box"
    """Textual CSS classes."""

    # --------------------------------------------------
    # Textual methods.
    # --------------------------------------------------
    def compose(self) -> ComposeResult:
        """Compose column widgets."""
        yield Static("▶ " + self.TITLE, classes="column-title")
        yield DataTable(id="table")

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_apply(self, action: str = "default") -> None:
        """Apply an action to selected rows."""
        selected_rows = [cast("Row", row) for row in self.table.selected_rows]
        if not selected_rows:
            selected_rows.append(cast("Row", self.table.current_row))
        if self.THREADED:
            for row in selected_rows:
                self.run_worker(partial(self.apply, action=action, row=row), thread=True)
        else:
            for row in selected_rows:
                self.apply(action=action, row=row)

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    @property
    def table(self) -> DataTable:
        """Data table."""
        return self.query_one("#table", DataTable)

    def update(self) -> None:
        """Update the column (ask the app to recompute its data)."""
        scan = getattr(self.app, "scan", None)
        if scan is not None:
            scan([self])

    def _reset(self) -> None:
        """Prepare the column for (re)population: restore styles, clear the table, show a loading indicator."""
        title = self.query_one(".column-title", Static)
        title.styles.text_style = None
        title.update("▶ " + self.TITLE)
        self.styles.width = None
        table = self.table
        table.styles.display = "block"
        table.clear(columns=True)
        table.cursor_type = "row"
        for header in self.HEADERS:
            table.add_column(header, key=header.lower())
        table.loading = True

    def _extend(self, rows: Iterable[tuple[Any, ...]]) -> None:
        """Add rows to the table, keeping it sorted."""
        table = self.table
        table.loading = False
        table.add_rows(rows)
        if self.HEADERS:
            table.sort(self.HEADERS[0].lower())

    def _mark_cached(self) -> None:
        """Show that the column currently displays cached (possibly stale) data."""
        title = self.query_one(".column-title", Static)
        title.update(f"▶ {self.TITLE} [dim](cached)[/dim]")

    def _finalize(self) -> None:
        """Finish a population cycle, collapsing the column if it's empty."""
        table = self.table
        table.loading = False
        if not table.row_count:
            title = self.query_one(".column-title", Static)
            title.styles.text_style = "bold"
            title.update("▼ " + self.TITLE)
            self.styles.width = 3
            table.styles.display = "none"

    # --------------------------------------------------
    # Methods to implement in subclasses.
    # --------------------------------------------------
    def list_projects(self) -> Iterable[Project]:
        """List projects for this column."""
        return ()

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Any, ...]]:  # noqa: ARG004
        """Populate rows for this column."""
        return []

    def apply(self, action: str, row: Row) -> None:  # noqa: ARG002
        """Apply action on given row."""
        return
