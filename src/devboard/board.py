"""The Textual application."""

from __future__ import annotations

import os
from functools import partial
from multiprocessing import Pool
from typing import TYPE_CHECKING, Any, Iterable

from textual import work
from textual.containers import Container
from textual.widgets import Static

from devboard.datatable import SelectableRow, SelectableRowsDataTable
from devboard.modal import ModalMixin
from devboard.notifications import NotifyMixin
from devboard.projects import Project

if TYPE_CHECKING:
    from textual.app import ComposeResult

DEBUG = os.getenv("DEBUG", "0") == "1"


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


class Column(Container, ModalMixin, NotifyMixin):  # type: ignore[misc]
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

    def on_mount(self) -> None:
        """Fill data table."""
        self.update()

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_apply(self, action: str = "default") -> None:
        """Apply an action to selected rows."""
        selected_rows = list(self.table.selected_rows) or [self.table.current_row]
        if self.THREADED:
            for row in selected_rows:
                self.run_worker(partial(self.apply, action=action, row=row), thread=True)
        else:
            for row in selected_rows:
                self.apply(action=action, row=row)  # type: ignore[arg-type]

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    @property
    def table(self) -> DataTable:
        """Data table."""
        return self.query_one("#table")  # type: ignore[return-value]

    def update(self) -> None:
        """Update the column (recompute data)."""
        table = self.query_one(DataTable)
        if table.loading:
            return
        table.loading = True
        table.clear(columns=True)
        table.cursor_type = "row"
        self._load_data(table)

    @work(thread=True)
    def _load_data(self, table: DataTable) -> None:
        if rows := self._populate():
            # TODO: Reset styles.
            for column in self.HEADERS:
                table.add_column(column, key=column.lower())
            table.add_rows(rows)
            table.sort(self.HEADERS[0].lower())
            table.refresh(layout=True)
        else:
            title: Static = self.query_one(".column-title")  # type: ignore[assignment]
            self.styles.width = 3
            title.styles.text_style = "bold"
            title.renderable = "▼ " + self.TITLE
            self.table.styles.display = "none"
        table.loading = False

    def _populate(self) -> list[tuple[Any, ...]]:
        rows = []
        if DEBUG:
            for project in self.list_projects():
                rows.extend(self.populate_rows(project))
        else:
            with Pool() as pool:
                for result in pool.map(self.populate_rows, self.list_projects()):
                    rows.extend(result)
        return rows

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
