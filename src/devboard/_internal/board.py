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
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.reactive import Reactive, reactive
from textual.widgets import Static
from textual.widgets.data_table import CellDoesNotExist

from devboard._internal.datatable import SelectableRow, SelectableRowsDataTable
from devboard._internal.modal import ModalMixin
from devboard._internal.notifications import NotifyMixin

if TYPE_CHECKING:
    from collections.abc import Hashable, Iterable, Iterator

    from textual.app import ComposeResult

_ItemT = TypeVar("_ItemT")


class Row(SelectableRow[_ItemT], Generic[_ItemT]):
    """A Devboard row."""

    def _for_worker(self) -> Row[_ItemT]:
        """Copy this Devboard row for safe use in a background worker."""
        return cast("Row[_ItemT]", super()._for_worker())

    @property
    def previous(self) -> Row[_ItemT]:
        """Previous Devboard row."""
        return cast("Row[_ItemT]", super().previous)

    @property
    def next(self) -> Row[_ItemT]:
        """Next Devboard row."""
        return cast("Row[_ItemT]", super().next)


class DataTable(SelectableRowsDataTable[_ItemT], Generic[_ItemT]):
    """A Devboard data table."""

    ROW = Row
    """The class to instantiate rows."""

    @property
    def current_row(self) -> Row[_ItemT]:
        """Currently selected row."""
        return cast("Row[_ItemT]", super().current_row)

    @property
    def selectable_rows(self) -> Iterator[Row[_ItemT]]:
        """Rows, as Devboard rows."""
        return cast("Iterator[Row[_ItemT]]", super().selectable_rows)

    @property
    def selected_rows(self) -> Iterator[Row[_ItemT]]:
        """Selected Devboard rows."""
        return cast("Iterator[Row[_ItemT]]", super().selected_rows)


class Column(Container, ModalMixin, NotifyMixin, Generic[_ItemT]):
    """A Devboard column."""

    BINDINGS: ClassVar = [
        Binding("c", "toggle_collapse", "Collapse/expand column"),
        Binding("m", "toggle_maximize", "Maximize/unmaximize column"),
    ]
    """Column key bindings."""
    is_collapsed: Reactive[bool] = reactive(default=False, init=False, layout=True, toggle_class="-collapsed")
    """Whether the column is collapsed."""
    is_cached: Reactive[bool] = reactive(default=False, init=False)
    """Whether the column displays cached data."""
    _layout_before_maximize: list[tuple[Column, bool, bool]] | None = None
    TITLE: str = ""
    """The title of the column."""
    HEADERS: tuple[str, ...] = ()
    """The data table headers."""
    CACHE_VERSION: int = 1
    """Version of the column's serialized cell format."""
    THREADED: bool = True
    """Whether actions of this column should run in the background."""
    DEFAULT_CLASSES = "box"
    """Textual CSS classes."""
    DEFAULT_CSS = """
    Column.-collapsed {
        width: 3;
    }

    Column.-collapsed .column-title {
        text-style: bold;
    }

    Column.-collapsed DataTable {
        display: none;
    }
    """
    """Styles owned by the reusable column widget."""

    # --------------------------------------------------
    # Textual methods.
    # --------------------------------------------------
    def compose(self) -> ComposeResult:
        """Compose column widgets."""
        yield Static("▶ " + self.TITLE, classes="column-title")
        yield DataTable(id="table")

    def _watch_is_collapsed(self) -> None:
        """Update the column when its collapsed state changes."""
        self._refresh_presentation()
        if self.is_mounted:
            self.app.call_after_refresh(self._refresh_resized_tables)

    def _watch_is_cached(self) -> None:
        """Update the title when the cache state changes."""
        self._refresh_presentation()

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_toggle_collapse(self) -> None:
        """Collapse or expand the column."""
        if self.is_collapsed:
            self._expand()
            self.screen.set_focus(self.table)
        else:
            self._collapse(focusable=True)
            self.screen.set_focus(self)

    def action_toggle_maximize(self) -> None:
        """Maximize the column or restore the layout from before it was maximized."""
        if self._layout_before_maximize is None:
            columns = list(self.screen.query(Column))
            self._layout_before_maximize = [(column, column.is_collapsed, column.can_focus) for column in columns]
            for column in columns:
                if column is self:
                    column._expand()
                else:
                    column._collapse()
            self.screen.set_focus(self.table)
            return

        layout = self._layout_before_maximize
        self._layout_before_maximize = None
        for column, was_collapsed, was_focusable in layout:
            if was_collapsed:
                column._collapse(focusable=was_focusable)
            else:
                column._expand()
        self.screen.set_focus(self if self.is_collapsed else self.table)

    def action_apply(self, action: str = "default") -> None:
        """Apply an action to selected rows."""
        selected_rows = list(self.table.selected_rows)
        if not selected_rows:
            try:
                selected_rows.append(self.table.current_row)
            except CellDoesNotExist:
                return
        action_rows = [row._for_worker() for row in selected_rows]
        if self.THREADED:
            for row in action_rows:
                self.run_worker(partial(self.apply, action=action, row=row), thread=True)
        else:
            for row in action_rows:
                self.apply(action=action, row=row)

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    @property
    def table(self) -> DataTable[_ItemT]:
        """Data table."""
        return cast("DataTable[_ItemT]", self.query_one("#table", DataTable))

    def update(self) -> None:
        """Update the column (ask the app to recompute its data)."""
        refresh_board = getattr(self.app, "refresh_board", None)
        if refresh_board is not None:
            self.app.call_later(refresh_board, [self])

    def serialize_cell(self, value: Any) -> Any:
        """Convert a cell value to data that the cache can store."""
        return value

    def deserialize_cell(self, value: Any) -> Any:
        """Restore a cell value loaded from the cache."""
        return value

    def _reset(self) -> None:
        """Prepare the column for (re)population: restore styles, clear the table, show a loading indicator."""
        restore_table_focus = self.has_focus
        self.is_cached = False
        self._expand()
        table = self.table
        if restore_table_focus:
            self.screen.set_focus(table)
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

    def _extend_item(self, item: _ItemT, rows: Iterable[tuple[Any, ...]]) -> None:
        """Add rows and associate them with the item that produced them."""
        with self.table._associate_rows(item):
            self._extend(rows)

    def _mark_cached(self) -> None:
        """Show that the column currently displays cached (possibly stale) data."""
        self.is_cached = True

    def _collapse(self, *, focusable: bool = False) -> None:
        """Hide the table and optionally keep the column focusable."""
        self.is_collapsed = True
        self.can_focus = focusable
        self._refresh_presentation()

    def _expand(self) -> None:
        """Show the table at its normal width."""
        self.is_collapsed = False
        self.can_focus = False
        self._refresh_presentation()

    def _refresh_presentation(self) -> None:
        """Project the column state into CSS classes and title text."""
        if not self.is_mounted:
            return
        if self.is_collapsed:
            text = "▼ " + self.TITLE
        else:
            suffix = " [dim](cached)[/dim]" if self.is_cached else ""
            text = f"▶ {self.TITLE}{suffix}"
        self.query_one(".column-title", Static).update(text)

    def _refresh_resized_tables(self) -> None:
        """Repaint table rows after a column changes the available width."""
        for table in self.screen.query(DataTable):
            table.force_refresh()

    def _finalize(self) -> None:
        """Finish a population cycle, collapsing the column if it's empty."""
        table = self.table
        table.loading = False
        if not table.row_count:
            self._collapse()

    # --------------------------------------------------
    # Methods to implement in subclasses.
    # --------------------------------------------------
    def list_items(self) -> Iterable[_ItemT]:
        """List the items to scan for this column."""
        return ()

    def item_key(self, item: _ItemT, /) -> Hashable:
        """Return the identity used to share and cache an item.

        Keys must be hashable and unique across the board.
        Objects can expose a `devboard_key` attribute to provide a stable
        identity. Hashable objects otherwise use their own identity. Unhashable
        objects use their process-local identity and should override this method
        if their rows need to be restored from the on-disk cache.
        """
        key = getattr(item, "devboard_key", item)
        try:
            hash(key)
        except TypeError:
            return id(item)
        return cast("Hashable", key)

    def populate_rows(self, item: _ItemT, /) -> list[tuple[Any, ...]]:  # noqa: ARG002
        """Build table rows for an item."""
        return []

    def apply(self, action: str, row: Row[_ItemT]) -> None:  # noqa: ARG002
        """Apply action on given row."""
        return


class Board:
    """A set of columns and the policies used to refresh their items."""

    def __init__(
        self,
        columns: Iterable[Column | type[Column]],
        *,
        bindings: Iterable[BindingType] = (),
        force_refresh_on_startup: bool = False,
    ) -> None:
        """Initialize the board.

        Parameters:
            columns: Column instances or classes displayed by the board.
            bindings: Application bindings owned by the board.
            force_refresh_on_startup: Whether startup uses the forced item hook.
        """
        self.columns: tuple[Column | type[Column], ...] = tuple(columns)
        """Column instances or classes displayed by the board."""
        self.bindings: tuple[BindingType, ...] = tuple(bindings)
        """Application bindings owned by the board."""
        self.force_refresh_on_startup: bool = force_refresh_on_startup
        """Whether startup uses the forced item hook."""

    def refresh_item(self, item: Any, /) -> None:
        """Prepare one item for a normal scan."""

    def force_refresh_item(self, item: Any, /) -> None:
        """Prepare one item for a forced scan."""
        self.refresh_item(item)
