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

from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from textual import on
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.widgets import DataTable
from textual.widgets.data_table import CellDoesNotExist, RowDoesNotExist, RowKey

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from textual.app import App

_ItemT = TypeVar("_ItemT")
_MISSING_ITEM = object()


@dataclass
class Checkbox:
    """A checkbox, added to rows to make them selectable."""

    checked: bool = False
    """Whether the checkbox is checked."""

    def __str__(self) -> str:
        return "■" if self.checked else ""

    def __rich__(self) -> str:
        return "[b]■[/]" if self.checked else ""

    def check(self) -> None:
        """Uncheck the checkbox."""
        self.checked = True

    def uncheck(self) -> None:
        """Uncheck the checkbox."""
        self.checked = False

    def toggle(self) -> bool:
        """Toggle the checkbox."""
        self.checked = not self.checked
        return self.checked


class _RemoveRow(Message):
    """Ask a data table to remove a row on the UI thread."""

    def __init__(self, key: RowKey) -> None:
        super().__init__()
        self.key = key


@dataclass
class SelectableRow(Generic[_ItemT]):
    """A selectable row."""

    table: SelectableRowsDataTable[_ItemT]
    """The data table containing this row."""
    key: RowKey
    """The row key."""
    _snapshot: list | None = field(default=None, repr=False)
    """Stable row data used by background actions."""
    _item_snapshot: _ItemT | object = field(default=_MISSING_ITEM, repr=False)
    """Stable source item used by background actions."""

    @property
    def app(self) -> App:
        """Textual application."""
        return self.table.app

    @property
    def _data(self) -> list:
        return self._snapshot if self._snapshot is not None else self.table.get_row(self.key)

    @property
    def data(self) -> list:
        """Row data (without checkbox)."""
        return self._data[1:]

    @property
    def item(self) -> _ItemT:
        """Item that produced this row.

        Raises:
            ValueError: If the row was added without a source item.
        """
        if self._item_snapshot is not _MISSING_ITEM:
            return cast("_ItemT", self._item_snapshot)
        return self.table._get_row_item(self.key)

    @property
    def index(self) -> int:
        """Row index."""
        return self.table.get_row_index(self.key)

    @property
    def checkbox(self) -> Checkbox:
        """Row checkbox."""
        return self._data[0]

    def select(self) -> None:
        """Select this row."""
        self.checkbox.check()

    def unselect(self) -> None:
        """Unselect this row."""
        self.checkbox.uncheck()

    def toggle_select(self) -> bool:
        """Toggle-select this row."""
        return self.checkbox.toggle()

    @property
    def selected(self) -> bool:
        """Whether this row is selected."""
        return self.checkbox.checked

    def remove(self) -> None:
        """Ask the table to remove this row on the UI thread."""
        self.table.post_message(_RemoveRow(self.key))

    def _for_worker(self) -> SelectableRow[_ItemT]:
        """Copy the row data for safe use in a background worker."""
        data = [Checkbox(self.checkbox.checked), *self.data]
        item = self.table._row_items.get(self.key, _MISSING_ITEM)
        return self.__class__(table=self.table, key=self.key, _snapshot=data, _item_snapshot=item)

    @property
    def previous(self) -> SelectableRow[_ItemT]:
        """Previous row (up)."""
        new_coord = Coordinate(self.index - 1, 0)
        key = self.table.coordinate_to_cell_key(new_coord).row_key
        return self.__class__(table=self.table, key=key)

    @property
    def next(self) -> SelectableRow[_ItemT]:
        """Next row (down)."""
        new_coord = Coordinate(self.index + 1, 0)
        key = self.table.coordinate_to_cell_key(new_coord).row_key
        return self.__class__(table=self.table, key=key)


class SelectableRowsDataTable(DataTable, Generic[_ItemT]):
    """Data table with selectable rows."""

    ROW = SelectableRow
    """The class to instantiate selectable rows."""

    BINDINGS: ClassVar = [
        Binding("space", "toggle_select_row", "Toggle select", show=False),
        Binding("ctrl+a, *", "toggle_select_all", "Toggle select all", show=False),
        Binding("exclamation_mark", "reverse_select", "Reverse select", show=False),
        Binding("shift+up", "toggle_select_up", "Expand select up", show=False),
        Binding("shift+down", "toggle_select_down", "Expand select down", show=False),
    ]
    """Key bindings for selecting rows."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the table and its row-to-item associations."""
        self._row_items: dict[RowKey, _ItemT] = {}
        self._associated_item: _ItemT | object = _MISSING_ITEM
        super().__init__(*args, **kwargs)

    # --------------------------------------------------
    # Textual methods.
    # --------------------------------------------------
    def add_row(
        self,
        *cells: Any,
        height: int | None = 1,
        key: str | None = None,
        label: Any | None = None,
    ) -> RowKey:
        """Add a row with a checkbox and associate its source item, if set."""
        row_key = super().add_row(Checkbox(), *cells, height=height, key=key, label=label)
        if self._associated_item is not _MISSING_ITEM:
            self._row_items[row_key] = cast("_ItemT", self._associated_item)
        return row_key

    def add_rows(self, rows: Iterable[Iterable]) -> list[RowKey]:
        """Add rows.

        Automatically insert a column with checkboxes in position 0.
        """
        return [self.add_row(*row) for row in rows]

    def clear(self, columns: bool = True) -> SelectableRowsDataTable[_ItemT]:  # noqa: FBT001,FBT002
        """Clear rows and optionally columns.

        When clearing columns, automatically re-add a column for checkboxes.
        """
        super().clear(columns)
        self._row_items.clear()
        if columns:
            self.add_column("", key="checkbox")
        return self

    def remove_row(self, row_key: RowKey | str) -> None:
        """Remove a row and its source-item association."""
        key = RowKey(row_key) if isinstance(row_key, str) else row_key
        self._row_items.pop(key, None)
        super().remove_row(row_key)

    # --------------------------------------------------
    # Message handlers.
    # --------------------------------------------------
    @on(_RemoveRow)
    def _on_remove_row(self, event: _RemoveRow) -> None:
        """Remove a row requested by foreground or background code."""
        event.stop()
        with suppress(RowDoesNotExist):
            self.remove_row(event.key)

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_toggle_select_row(self) -> None:
        """Toggle-select current row."""
        try:
            row = self.current_row
        except CellDoesNotExist:
            return
        row.toggle_select()
        self.force_refresh()

    def action_toggle_select_all(self) -> None:
        """Toggle-select all rows."""
        rows = list(self.selectable_rows)
        if all(row.selected for row in rows):
            for row in rows:
                row.unselect()
        else:
            for row in rows:
                row.select()
        self.force_refresh()

    def action_reverse_select(self) -> None:
        """Reverse selection."""
        for row in self.selectable_rows:
            row.toggle_select()
        self.force_refresh()

    def action_toggle_select_up(self) -> None:
        """Toggle selection up."""
        try:
            row = self.current_row
            previous_row = row.previous
        except CellDoesNotExist:
            pass
        else:
            previous_row.toggle_select()
            self.move_cursor(row=previous_row.index)
            self.force_refresh()

    def action_toggle_select_down(self) -> None:
        """Toggle selection down."""
        try:
            row = self.current_row
            next_row = row.next
        except CellDoesNotExist:
            pass
        else:
            next_row.toggle_select()
            self.move_cursor(row=next_row.index)
            self.force_refresh()

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    @contextmanager
    def _associate_rows(self, item: _ItemT) -> Iterator[None]:
        """Associate rows added in this context with their source item."""
        previous_item = self._associated_item
        self._associated_item = item
        try:
            yield
        finally:
            self._associated_item = previous_item

    def _get_row_item(self, key: RowKey) -> _ItemT:
        """Return the item associated with a row."""
        try:
            return self._row_items[key]
        except KeyError as error:
            raise ValueError("No item is associated with this row") from error

    def force_refresh(self) -> None:
        """Force refresh table."""
        for row in self.selectable_rows:
            self.update_cell(row.key, "checkbox", row.checkbox)

    @property
    def current_row(self) -> SelectableRow[_ItemT]:
        """Currently selected row."""
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        return self.ROW(table=self, key=key)

    @property
    def selectable_rows(self) -> Iterator[SelectableRow[_ItemT]]:
        """Rows, as selectable ones."""
        for key in self.rows:
            yield self.ROW(table=self, key=key)

    @property
    def selected_rows(self) -> Iterator[SelectableRow[_ItemT]]:
        """Selected rows."""
        for row in self.selectable_rows:
            if row.selected:
                yield row
