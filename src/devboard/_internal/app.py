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

import os
from collections.abc import Hashable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.markdown import Markdown
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Footer, Static
from textual.worker import NoActiveWorker, Worker, get_current_worker

from devboard._internal import cache
from devboard._internal.board import Board, Column, DataTable
from devboard._internal.loader import _load_board as _load_board_definition
from devboard._internal.modal import Modal, ModalMixin

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_ItemIdentity = Hashable
_ItemRows = tuple[Any, list[tuple[Any, ...]]]

_DEBUG = os.getenv("DEBUG", "0") == "1"

_DEFAULT_WORKERS = 4
"""Default number of concurrent workers scanning items.

Kept deliberately low because too many concurrent project scans on a cold
cache (e.g. right after boot) make spinning disks seek-thrash. A few readers
are faster in that situation.
"""


class _Progress(Message):
    """Update or clear progress for one source."""

    def __init__(self, source: object, description: str | None) -> None:
        super().__init__()
        self.source = source
        self.description = description


class Devboard(App, ModalMixin, inherit_bindings=False):
    """The Devboard application."""

    CSS_PATH = Path(__file__).parent / "devboard.tcss"
    """Path to the CSS file."""

    # --------------------------------------------------
    # Textual methods.
    # --------------------------------------------------
    def __init__(
        self,
        *args: Any,
        board: str | Path | None = None,
        background_tasks: bool = True,
        workers: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the app.

        Parameters:
            board: The board to display (name or file path).
            background_tasks: Whether to run forced startup hooks and use the on-disk cache.
                Disable this option for deterministic tests and screenshots.
            workers: How many items to scan concurrently. Overrides the `workers` config setting.
        """
        super().__init__(*args, **kwargs)
        self._board_source: str | Path | None = board
        self._board_key: str = str(board)
        self._background_tasks: bool = background_tasks
        self._scan_workers: int | None = workers
        self._scanning: bool = False
        self._progress_by_source: dict[object, str] = {}
        self._progress = Static("", id="task-progress", markup=False)
        self.board: Board = self._load_board()
        """The loaded board definition."""
        self._columns = self.board.columns
        self._bind_board_actions()

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        for column in self._columns:
            if isinstance(column, Column):
                yield column
            else:
                yield column()
        with Vertical(id="status-bar"):
            yield self._progress
            yield Footer()

    def on_mount(self) -> None:
        """Populate columns when the application starts."""
        force = self._background_tasks and self.board.force_refresh_on_startup
        self.scan(initial=True, force=force)

    @on(_Progress)
    def _on_progress(self, event: _Progress) -> None:
        source = event.source
        self._progress_by_source.pop(source, None)
        if event.description is not None and not (
            isinstance(source, Worker) and (source.is_finished or source.is_cancelled)
        ):
            # Keep the most recent update last, even when progress sources overlap.
            self._progress_by_source[source] = event.description
        self._refresh_task_progress()

    @on(Worker.StateChanged)
    def _on_task_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.is_finished:
            self._progress_by_source.pop(event.worker, None)
            self._refresh_task_progress()

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_show_help(self) -> None:
        """Show help."""
        lines = ["# Main keys\n\n"]
        lines.extend(self._binding_specs_help(self.board.bindings))
        lines.extend(self._bindings_help(DataTable, search_up=True))
        lines.extend(self._bindings_help(Column))
        for column in self.query(Column):
            lines.append(f"\n\n# {column.__class__.TITLE}\n\n")
            lines.extend(self._bindings_help(column.__class__))
        self.push_screen(Modal(text=Markdown("\n".join(lines))))

    def action_refresh(self) -> None:
        """Refresh all columns."""
        self.refresh_board()

    def action_force_refresh(self) -> None:
        """Force-refresh all columns."""
        self.force_refresh_board()

    def action_exit(self) -> None:
        """Exit application."""
        self.workers.cancel_all()
        self.exit()

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    def _refresh_task_progress(self) -> None:
        description = next(reversed(self._progress_by_source.values()), "")
        self._progress.update(Text(description, no_wrap=True, overflow="ellipsis"))

    def _report_progress(self, source: object, description: str | None) -> None:
        """Post a progress update from a column or its active worker."""
        with suppress(NoActiveWorker):
            source = get_current_worker()
        self.post_message(_Progress(source, description))

    def refresh_board(self, columns: Iterable[Column] | None = None) -> None:
        """Refresh columns without forcing their items to update external state."""
        self.scan(columns)

    def force_refresh_board(self, columns: Iterable[Column] | None = None) -> None:
        """Refresh columns after forcing their items to update external state."""
        self.scan(columns, force=True)

    def _update_cache(self) -> None:
        """Save the board currently displayed after a row operation."""
        if self._background_tasks:
            cache._save(self._board_key, self._cache_data(), schema=self._cache_schema())

    def scan(
        self,
        columns: Iterable[Column] | None = None,
        *,
        initial: bool = False,
        force: bool = False,
    ) -> None:
        """Recompute columns data in the background.

        A single scan feeds all columns: each item is read once,
        by a small pool of threads, and the resulting rows are dispatched
        to every column as they arrive. Each completed scan saves the displayed
        board to the cache when background tasks are enabled.

        Parameters:
            columns: The columns to update (all of them by default).
            initial: Whether this is the initial scan, which can display cached data.
            force: Whether to use the board's forced item hook.
        """
        if self._scanning:
            return
        self._scanning = True
        column_list = list(columns) if columns is not None else list(self.query(Column))
        self.run_worker(partial(self._scan, column_list, initial=initial, force=force), thread=True)

    def _scan(self, columns: list[Column], *, initial: bool, force: bool) -> None:
        worker = get_current_worker()
        call = self.call_from_thread
        use_cache = self._background_tasks
        try:
            schema = call(self._cache_schema) if use_cache else None
            # List items (fast) and share equivalent instances between columns.
            canonical, columns_by_item, items_by_column, item_order = self._collect_items(columns)

            # Display data cached during the previous scan, if any:
            # the board is filled instantly, even on a cold disk cache.
            streaming = True
            if initial and use_cache and (cached := cache._load(self._board_key, schema=schema)) is not None:
                cached_rows = {}
                for index, column in enumerate(columns):
                    key = str(index)
                    if key not in cached or not all(len(row["cells"]) == len(column.HEADERS) for row in cached[key]):
                        continue
                    decoded_rows = cache._decode_rows(cached[key], items_by_column[column])
                    cached_rows[column] = [
                        (item, tuple(column.deserialize_cell(value) for value in row)) for item, row in decoded_rows
                    ]
                if len(cached_rows) == len(columns):
                    call(self._show_cached_columns, cached_rows)
                    streaming = False

            if streaming:
                call(self._reset_columns, columns)

            # Prepare and scan each item in one thread so there is no barrier
            # between updating the item and computing its rows.
            results: dict[Column, list[_ItemRows]] = {column: [] for column in columns}
            pending: dict[Column, dict[_ItemIdentity, _ItemRows]] = {column: {} for column in columns}
            next_item: dict[Column, int] = dict.fromkeys(columns, 0)
            prepare_item = self.board.force_refresh_item if force else self.board.refresh_item

            def scan_item(identity: _ItemIdentity) -> list[tuple[Column, Any, list[tuple[Any, ...]]]]:
                item = canonical[identity]
                if worker.is_cancelled:
                    return []
                try:
                    prepare_item(item)
                except Exception as error:  # noqa: BLE001
                    self.log.error(f"Could not prepare {item} for scanning: {error}")  # noqa: TRY400
                rows_by_column = []
                for column in columns_by_item[identity]:
                    try:
                        rows = column.populate_rows(item)
                    except Exception as error:  # noqa: BLE001
                        self.log.error(f"Could not scan {item}: {error}")  # noqa: TRY400
                        rows = []
                    rows_by_column.append((column, item, rows))
                return rows_by_column

            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                futures = {pool.submit(scan_item, identity): identity for identity in columns_by_item}
                for done, future in enumerate(as_completed(futures), start=1):
                    if worker.is_cancelled:
                        pool.shutdown(wait=False, cancel_futures=True)
                        return
                    identity = futures[future]
                    completed_columns = []
                    for column, item, rows in future.result():
                        pending[column][identity] = (item, rows)
                        completed_columns.append(column)
                    for column in completed_columns:
                        order = item_order[column]
                        index = next_item[column]
                        while index < len(order) and order[index] in pending[column]:
                            item, rows = pending[column].pop(order[index])
                            if rows:
                                results[column].append((item, rows))
                                if streaming:
                                    call(column._extend_item, item, rows)
                            index += 1
                        next_item[column] = index
                    item = canonical[identity]
                    verb = "Force-refreshed" if force else "Refreshed"
                    self.post_message(_Progress(worker, f"{verb} {item} ({done}/{len(futures)})"))

            if streaming:
                call(self._finalize_columns, columns)
            else:
                call(self._refresh_columns, results)

            if use_cache:
                cache._save(self._board_key, call(self._cache_data), schema=schema)
        finally:
            call(self._finish_scan)

    def _finish_scan(self) -> None:
        """Mark the current scan as finished on the UI thread."""
        self._scanning = False

    @property
    def _max_workers(self) -> int:
        if _DEBUG:
            return 1
        return max(1, self._scan_workers or _DEFAULT_WORKERS)

    def _reset_columns(self, columns: list[Column]) -> None:
        for column in columns:
            column._reset()

    def _finalize_columns(self, columns: list[Column]) -> None:
        for column in columns:
            column._finalize()

    def _refresh_columns(self, results: dict[Column, list[_ItemRows]]) -> None:
        for column, item_rows in results.items():
            column._reset()
            for item, rows in item_rows:
                column._extend_item(item, rows)
            column._finalize()

    def _show_cached_columns(self, cached_rows: dict[Column, list[tuple[Any, tuple[Any, ...]]]]) -> None:
        for column, item_rows in cached_rows.items():
            column._reset()
            for item, row in item_rows:
                column._extend_item(item, [row])
            if item_rows:
                column._mark_cached()
            column._finalize()

    def _cache_schema(self) -> list[list[str]]:
        """Identify the ordered column types, IDs, titles, and headers in a snapshot."""
        return [
            [
                f"{type(column).__module__}.{type(column).__qualname__}",
                column.id or "",
                column.TITLE,
                str(column.CACHE_VERSION),
                *column.HEADERS,
            ]
            for column in self.query(Column)
        ]

    def _cache_data(self) -> dict[str, list[cache._CachedRow]]:
        """Snapshot all displayed columns, including those not recomputed by a partial scan."""
        return {
            str(index): [
                cache._CachedRow(
                    item_key=column.item_key(row.item),
                    item=row.item,
                    cells=tuple(value if value is row.item else column.serialize_cell(value) for value in row.data),
                )
                for row in column.table.selectable_rows
            ]
            for index, column in enumerate(self.query(Column))
        }

    @staticmethod
    def _collect_items(
        columns: list[Column],
    ) -> tuple[
        dict[_ItemIdentity, Any],
        dict[_ItemIdentity, list[Column]],
        dict[Column, dict[str, Any]],
        dict[Column, list[_ItemIdentity]],
    ]:
        """List items and build their scan and cache lookups."""
        canonical: dict[_ItemIdentity, Any] = {}
        columns_by_item: dict[_ItemIdentity, list[Column]] = {}
        items_by_column: dict[Column, dict[str, Any]] = {column: {} for column in columns}
        item_order: dict[Column, list[_ItemIdentity]] = {column: [] for column in columns}
        for column in columns:
            for candidate in column.list_items():
                identity = column.item_key(candidate)
                item = canonical.setdefault(identity, candidate)
                interested_columns = columns_by_item.setdefault(identity, [])
                if column not in interested_columns:
                    interested_columns.append(column)
                    item_order[column].append(identity)
                items_by_column[column][cache._item_token(column.item_key(item))] = item
        return canonical, columns_by_item, items_by_column, item_order

    def _load_board(self) -> Board:
        """Load the board and its settings before composing the widget tree."""
        definition = _load_board_definition(self._board_source)
        self._board_key = str(definition.path)
        if self._scan_workers is None:
            self._scan_workers = definition.workers
        return definition.board

    def _bind_board_actions(self) -> None:
        """Install the application bindings declared by the board."""
        for spec in self.board.bindings:
            binding = spec if isinstance(spec, Binding) else Binding(*spec)
            self.bind(
                binding.key,
                binding.action,
                description=binding.description,
                show=binding.show,
                key_display=binding.key_display,
            )

    @staticmethod
    def _bindings_help(cls: type, *, search_up: bool = False) -> Iterator[str]:  # noqa: PLW0211
        bindings = getattr(cls, "BINDINGS", []) if search_up else cls.__dict__.get("BINDINGS", [])
        for binding in bindings:
            if isinstance(binding, tuple):
                binding = Binding(*binding)  # noqa: PLW2901
            keys = "`, `".join(key.strip().upper().replace("+", "-") for key in binding.key.split(","))
            yield f"- `{keys}`: {binding.description}"

    @staticmethod
    def _binding_specs_help(bindings: Iterable[Binding | tuple[str, str] | tuple[str, str, str]]) -> Iterator[str]:
        """Format board binding descriptions for the help screen."""
        for binding in bindings:
            if isinstance(binding, tuple):
                binding = Binding(*binding)  # noqa: PLW2901
            keys = "`, `".join(key.strip().upper().replace("+", "-") for key in binding.key.split(","))
            yield f"- `{keys}`: {binding.description}"
