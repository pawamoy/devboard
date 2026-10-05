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

import asyncio
from contextlib import suppress
from functools import partial, wraps
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

from textual import events, on
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import Reactive, reactive
from textual.widgets import Static
from textual.widgets.data_table import CellDoesNotExist, RowKey
from textual.worker import WorkerCancelled, WorkerFailed

from devboard._internal.datatable import SelectableRow, SelectableRowsDataTable
from devboard._internal.modal import ModalMixin
from devboard._internal.notifications import NotifyMixin

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Hashable, Iterable, Iterator

    from textual.app import ComposeResult
    from textual.worker import Worker

_ItemT = TypeVar("_ItemT")


class _TableEmptied(Message):
    """Report that a Devboard table lost its final row."""


class _TableRowsChanged(Message):
    """Report a change to the number of visible rows."""


class _RefreshItem(Message):
    """Request an item refresh from a row action."""

    def __init__(
        self,
        item: Any,
        source: Column,
        columns: tuple[Column | type[Column], ...] | None,
        *,
        force: bool,
    ) -> None:
        super().__init__()
        self.item = item
        self.source = source
        self.columns = columns
        self.force = force


class Row(SelectableRow[_ItemT], Generic[_ItemT]):
    """A Devboard row."""

    def refresh(self, *, columns: Iterable[Column | type[Column]] | None = None, force: bool = False) -> None:
        """Request a refresh of this row's item in the specified columns.

        Pass column instances or classes. Omit `columns` to refresh every column
        that lists the item. This method is safe in background actions and after
        `remove()` on an action's row snapshot. Requests wait for any active scan.
        Set `force=True` to use the board's forced item hook.
        """
        self.table.post_message(
            _RefreshItem(
                self.item,
                cast("Column", self.table.parent),
                tuple(columns) if columns is not None else None,
                force=force,
            ),
        )

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

    def add_row(self, *cells: Any, height: int | None = 1, key: str | None = None, label: Any | None = None) -> RowKey:
        """Add a row and update the column's row count."""
        row_key = super().add_row(*cells, height=height, key=key, label=label)
        self.post_message(_TableRowsChanged())
        return row_key

    def clear(self, columns: bool = True) -> DataTable[_ItemT]:  # noqa: FBT001,FBT002
        """Clear the table and update the column's row count."""
        super().clear(columns)
        self.post_message(_TableRowsChanged())
        return self

    def remove_row(self, row_key: RowKey | str) -> None:
        """Remove a row and report when the table becomes empty."""
        super().remove_row(row_key)
        self.post_message(_TableRowsChanged())
        if not self.row_count:
            self.post_message(_TableEmptied())

    def filter_rows(self, predicate: Callable[[SelectableRow[_ItemT]], bool] | None) -> None:
        """Filter rows and update the column's visible row count."""
        super().filter_rows(predicate)
        self.post_message(_TableRowsChanged())

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

    @property
    def all_rows(self) -> Iterator[Row[_ItemT]]:
        """All Devboard rows, including rows hidden by a filter."""
        return cast("Iterator[Row[_ItemT]]", super().all_rows)


class Column(Container, ModalMixin, NotifyMixin, Generic[_ItemT]):
    """A Devboard column."""

    BINDINGS: ClassVar = [
        Binding("ctrl+e", "toggle_collapse", "Collapse/expand column", show=False),
        # Terminals send Ctrl+M as Enter, so use Ctrl+X for maximization.
        Binding("ctrl+x", "toggle_maximize", "Maximize/unmaximize column", show=False),
    ]
    """Column key bindings."""
    is_collapsed: Reactive[bool] = reactive(default=False, init=False, layout=True, toggle_class="-collapsed")
    """Whether the column is collapsed."""
    is_cached: Reactive[bool] = reactive(default=False, init=False)
    """Whether the column displays cached data."""
    _layout_before_maximize: list[tuple[Column, bool]] | None = None
    TITLE: str = ""
    """The title of the column."""
    HEADERS: tuple[str, ...] = ()
    """The data table headers."""
    CACHE_VERSION: int = 1
    """Version of the column's serialized cell format."""
    THREADED: bool = True
    """Whether synchronous row actions run in background threads."""
    DEFAULT_CLASSES = "box"
    """Textual CSS classes."""
    DEFAULT_CSS = """
    Column .column-header {
        height: 1;
    }

    Column .column-title {
        width: 1fr;
        padding: 0 1;
        text-wrap: nowrap;
        text-overflow: ellipsis;
    }

    Column .column-count {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }

    Column.-collapsed {
        width: 3;
    }

    Column.-collapsed .column-header {
        height: auto;
    }

    Column.-collapsed .column-title {
        padding: 0;
        text-wrap: wrap;
        text-overflow: fold;
        text-style: bold;
    }

    Column.-collapsed .column-count {
        display: none;
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
        with Horizontal(classes="column-header"):
            yield Static("▶ " + self.TITLE, classes="column-title")
            yield Static("0", classes="column-count", markup=False)
        yield DataTable(id="table")

    @on(events.Focus)
    @on(events.Blur)
    @on(events.DescendantFocus)
    @on(events.DescendantBlur)
    def _update_title_focus(self) -> None:
        """Highlight the column when it or one of its descendants has focus."""
        self.set_class(self.has_focus_within, "-focused")

    @on(_TableRowsChanged)
    def _on_table_rows_changed(self, event: _TableRowsChanged) -> None:
        """Update the header after rows are added, removed, cleared, or filtered."""
        event.stop()
        self._refresh_presentation()

    def _watch_is_collapsed(self) -> None:
        """Update the column when its collapsed state changes."""
        self.can_focus = self.is_collapsed
        self._refresh_presentation()
        if self.is_mounted:
            if self.has_focus or self.table.has_focus:
                self.screen.set_focus(self if self.is_collapsed else self.table)
            self.app.call_after_refresh(self._refresh_resized_tables)

    def _watch_is_cached(self) -> None:
        """Update the title when the cache state changes."""
        self._refresh_presentation()

    @on(_TableEmptied)
    def _on_table_emptied(self, event: _TableEmptied) -> None:
        """Apply the empty-column state after the final row is removed."""
        event.stop()
        self._finalize()

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_toggle_collapse(self) -> None:
        """Collapse or expand the column."""
        self.is_collapsed = not self.is_collapsed
        self.screen.set_focus(self if self.is_collapsed else self.table)

    def action_toggle_maximize(self) -> None:
        """Maximize the column or restore the layout from before it was maximized."""
        if self._layout_before_maximize is None:
            columns = list(self.screen.query(Column))
            self._layout_before_maximize = [(column, column.is_collapsed) for column in columns]
            for column in columns:
                if column is self:
                    column._expand()
                else:
                    column._collapse()
            self.screen.set_focus(self.table)
            return

        layout = self._layout_before_maximize
        self._layout_before_maximize = None
        for column, was_collapsed in layout:
            if was_collapsed:
                column._collapse()
            else:
                column._expand()
        self.screen.set_focus(self if self.is_collapsed else self.table)

    def _action_rows(self) -> list[Row[_ItemT]]:
        """Snapshot the selected visible rows, or the current row."""
        selected_rows = list(self.table.selected_rows)
        if not selected_rows:
            with suppress(CellDoesNotExist):
                selected_rows.append(self.table.current_row)
        return [row._for_worker() for row in selected_rows]

    def _apply_to_rows(self, action: Callable[[Row[_ItemT]], Awaitable[None] | None]) -> None:
        """Run an action for each selected row, or for the current row."""
        self._start_row_operation([partial(action, row) for row in self._action_rows()])

    def _apply_to_row_batch(self, action: Callable[[list[Row[_ItemT]]], Awaitable[None] | None]) -> None:
        """Run an action once with the selected rows, or the current row."""
        rows = self._action_rows()
        self._start_row_operation([partial(action, rows)] if rows else [])

    def _start_row_operation(self, actions: list[Callable[[], Awaitable[None] | None]]) -> None:
        """Dispatch row callbacks and save their changes after completion."""
        workers: list[Worker[Exception | None]] = []
        errors: tuple[Exception, ...] = ()
        try:
            for action in actions:
                if iscoroutinefunction(action):
                    workers.append(
                        self.run_worker(self._run_async_row_action(cast("Callable[[], Awaitable[None]]", action))),
                    )
                elif self.THREADED:
                    workers.append(
                        self.run_worker(partial(self._run_row_action, cast("Callable[[], None]", action)), thread=True),
                    )
                else:
                    action()
        except Exception as error:  # noqa: BLE001
            errors = (error,)

        if not workers and not self.THREADED and getattr(self.app, "_update_cache", None) is None:
            if errors:
                raise errors[0]
            return
        self.run_worker(self._finish_row_operation(workers, errors))

    @staticmethod
    def _run_row_action(action: Callable[[], None]) -> Exception | None:
        """Run a threaded callback and return any error to the operation coordinator."""
        try:
            action()
        except Exception as error:  # noqa: BLE001
            return error
        return None

    @staticmethod
    async def _run_async_row_action(action: Callable[[], Awaitable[None]]) -> Exception | None:
        """Await an async callback and return any error to the operation coordinator."""
        try:
            await action()
        except Exception as error:  # noqa: BLE001
            return error
        return None

    async def _finish_row_operation(
        self,
        workers: list[Worker[Exception | None]],
        errors: tuple[Exception, ...] = (),
    ) -> None:
        """Update the cache once after every worker in a row operation finishes."""
        results = await asyncio.gather(*(worker.wait() for worker in workers), return_exceptions=True)
        await self._update_cache_after_messages()
        for result in (*errors, *results):
            if isinstance(result, WorkerCancelled):
                continue
            if isinstance(result, WorkerFailed):
                raise result.error
            if isinstance(result, Exception):
                raise result

    async def _update_cache_after_messages(self) -> None:
        """Wait for pending table messages, then update the cache."""
        update_cache = getattr(self.app, "_update_cache", None)
        if update_cache is None:
            return

        loop = asyncio.get_running_loop()
        updated = loop.create_future()

        def update() -> None:
            try:
                update_cache()
            except Exception as error:  # noqa: BLE001
                updated.set_exception(error)
            else:
                updated.set_result(None)

        if self.table.call_later(update):
            await updated

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

    def filter_rows(self, predicate: Callable[[Row[_ItemT]], bool] | None) -> None:
        """Show matching rows, or clear this column's filter with `None`.

        The predicate receives each row, including its source item and display
        cells. It also applies after refreshes. Call this method on the UI thread.
        """
        was_empty = not self.table.row_count
        self.table.filter_rows((lambda row: predicate(cast("Row[_ItemT]", row))) if predicate is not None else None)
        if was_empty and self.table.row_count:
            self._expand()
        self._finalize()

    def report_progress(self, description: str | None = None) -> None:
        """Show progress on the left of the footer.

        Devboard automatically clears progress associated with a worker when that worker finishes or is cancelled.

        Parameters:
            description: Progress text. Omit the text to clear the current progress.
        """
        report_progress = getattr(self.app, "_report_progress", None)
        if report_progress is not None:
            report_progress(self, description)

    def serialize_cell(self, value: Any) -> Any:
        """Convert a cell value to data that the cache can store."""
        return value

    def deserialize_cell(self, value: Any) -> Any:
        """Restore a cell value loaded from the cache."""
        return value

    def _reset(self) -> None:
        """Prepare the column for (re)population: restore styles, clear the table, show a loading indicator."""
        self.is_cached = False
        self._expand()
        table = self.table
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

    def _collapse(self) -> None:
        """Hide the table and keep the collapsed column focusable."""
        self.is_collapsed = True
        self._refresh_presentation()

    def _expand(self) -> None:
        """Show the table at its normal width."""
        self.is_collapsed = False
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
        self.query_one(".column-count", Static).update(str(self.table.row_count))

    def _refresh_resized_tables(self) -> None:
        """Repaint table rows after a column changes the available width."""
        for table in self.screen.query(DataTable):
            table.force_refresh()

    def _finalize(self) -> None:
        """Finish population and collapse columns with no visible rows."""
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


_ActionColumnT = TypeVar("_ActionColumnT", bound=Column[Any])


def row_action(
    method: Callable[[_ActionColumnT, Row[Any]], Awaitable[None] | None],
) -> Callable[[_ActionColumnT], None]:
    """Adapt a row callback into a Textual action.

    Decorate an `action_*` method and use the suffix as the binding action. For example, bind `open` to a decorated
    `action_open` method.

    The decorated method receives each selected row, or the current row when no rows are selected. Devboard runs each
    synchronous call in a background thread unless the column sets `THREADED` to false. Async methods run in async workers.
    When caching is enabled, Devboard updates the cache once after the whole operation, including no-ops and failed calls.
    """

    @wraps(method)
    def action(column: _ActionColumnT) -> None:
        column._apply_to_rows(partial(method, column))

    return action


def rows_action(
    method: Callable[[_ActionColumnT, list[Row[Any]]], Awaitable[None] | None],
) -> Callable[[_ActionColumnT], None]:
    """Adapt a batch callback into a Textual action.

    Decorate an `action_*` method and use its suffix in a binding. The method receives one list of selected visible rows,
    or a list containing the current row when none are selected. Empty tables do not call the method.

    Rows are stable snapshots, with the same `data`, `item`, `remove()`, and `refresh()` API as `row_action` callbacks.
    Synchronous methods run in one background thread unless the column sets `THREADED` to false. Async methods always
    run in an async worker, so they can await `self.app.push_screen_wait()` to ask for shared input.
    Use `asyncio.to_thread()` for blocking work inside an async method.

    When caching is enabled, Devboard updates the cache once after the operation, including no-ops and failed calls.
    """

    @wraps(method)
    def action(column: _ActionColumnT) -> None:
        column._apply_to_row_batch(partial(method, column))

    return action


class Board:
    """A set of columns and the policies used to refresh their items."""

    BINDINGS: ClassVar = [
        Binding("question_mark", "show_help", "Help"),
        # Keep Ctrl+C available for exit when text is selected.
        Binding("ctrl+c", "exit", "Exit", priority=True),
        Binding("escape", "exit", "Exit"),
        Binding("alt+r", "refresh_item", "Refresh item", show=False),
        Binding("alt+shift+r", "refresh_column", "Refresh column", show=False),
        Binding("ctrl+r", "refresh_board", "Refresh board", show=False),
        Binding("ctrl+shift+r", "force_refresh_board", "Force refresh board", show=False),
        Binding("ctrl+f", "filter_board", "Filter board", show=False),
    ]
    """Default application bindings used when a board does not specify its own."""

    def __init__(
        self,
        columns: Iterable[Column | type[Column]],
        *,
        bindings: Iterable[BindingType] | None = None,
        force_refresh_on_startup: bool = False,
    ) -> None:
        """Initialize the board.

        Parameters:
            columns: Column instances or classes displayed by the board.
            bindings: Application bindings owned by the board. Omit this argument to use `BINDINGS`.
                An explicit iterable replaces the defaults. An empty iterable disables them.
            force_refresh_on_startup: Whether startup uses the forced item hook.
        """
        self.columns: tuple[Column | type[Column], ...] = tuple(columns)
        """Column instances or classes displayed by the board."""
        self.bindings: tuple[BindingType, ...] = tuple(self.BINDINGS if bindings is None else bindings)
        """Application bindings owned by the board."""
        self.force_refresh_on_startup: bool = force_refresh_on_startup
        """Whether startup uses the forced item hook."""

    def refresh_item(self, item: Any, /) -> None:
        """Prepare one item for a normal scan."""

    def force_refresh_item(self, item: Any, /) -> None:
        """Prepare one item for a forced scan."""
        self.refresh_item(item)

    def matches_filter(self, row: Row[Any], value: str, /) -> bool:
        """Match filter text against displayed cells, ignoring case.

        Override this method to match source items instead. For example, a
        backlog board can compare `row.item.repository` with `value`.
        An empty filter shows every row.
        """
        return not value or any(value.casefold() in str(cell).casefold() for cell in row.data)
