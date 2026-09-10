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
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from appdirs import user_config_dir
from rich.markdown import Markdown
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer
from textual.worker import get_current_worker

from devboard._internal import cache
from devboard._internal.board import Column, DataTable
from devboard._internal.modal import Modal, ModalMixin

# TODO: Remove once support for Python 3.10 is dropped.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from devboard._internal.projects import Project

_DEBUG = os.getenv("DEBUG", "0") == "1"

_DEFAULT_WORKERS = 4
"""Default number of concurrent workers scanning projects.

Kept deliberately low: on cold caches (e.g. right after boot),
too many concurrent readers make spinning disks seek-thrash,
which is slower than a few sequential-ish readers.
"""


class Devboard(App, ModalMixin):
    """The Devboard application."""

    CSS_PATH = Path(__file__).parent / "devboard.tcss"
    """Path to the CSS file."""

    BINDINGS: ClassVar = [
        Binding("F5, ctrl+r", "refresh", "Refresh"),
        Binding("question_mark", "show_help", "Help"),
        Binding("ctrl+q, q, escape", "exit", "Exit", key_display="Q"),
    ]
    """Application key bindings."""

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
            background_tasks: Whether to fetch repositories in the background after the initial scan.
                Disabling this also disables the on-disk cache (useful for tests and screenshots).
            workers: How many projects to scan concurrently. Overrides the `workers` config setting.
        """
        super().__init__(*args, **kwargs)
        self._board: str | Path | None = board
        self._board_key: str = str(board)
        self._config_file: Path = Path(user_config_dir(), "devboard", "config.toml")
        self._background_tasks: bool = background_tasks
        self._scan_workers: int | None = workers
        self._scanning: bool = False

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        for column in self._load_columns():
            if isinstance(column, Column):
                yield column
            else:
                yield column()
        yield Footer()

    def on_mount(self) -> None:
        """Populate columns, then run background tasks."""
        self.scan(initial=True)

    # --------------------------------------------------
    # Binding actions.
    # --------------------------------------------------
    def action_show_help(self) -> None:
        """Show help."""
        lines = ["# Main keys\n\n"]
        lines.extend(self._bindings_help(Devboard))
        lines.extend(self._bindings_help(DataTable, search_up=True))
        for column in self.query(Column):
            lines.append(f"\n\n# {column.__class__.TITLE}\n\n")
            lines.extend(self._bindings_help(column.__class__))
        self.push_screen(Modal(text=Markdown("\n".join(lines))))

    def action_refresh(self) -> None:
        """Refresh all columns."""
        self.scan()

    def action_exit(self) -> None:
        """Exit application."""
        self.workers.cancel_all()
        self.exit()

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    def scan(self, columns: Iterable[Column] | None = None, *, initial: bool = False) -> None:
        """Recompute columns data in the background.

        A single scan feeds all columns: each project is read once,
        by a small pool of threads, and the resulting rows are dispatched
        to every column as they arrive.

        Parameters:
            columns: The columns to update (all of them by default).
            initial: Whether this is the initial scan at startup, which additionally
                displays cached data, saves fresh data to the cache, and triggers
                the background fetch when these features are enabled.
        """
        if self._scanning:
            return
        self._scanning = True
        column_list = list(columns) if columns is not None else list(self.query(Column))
        self.run_worker(partial(self._scan, column_list, initial=initial), thread=True)

    @work(thread=True)
    def fetch_all(self) -> None:
        """Run `git fetch` in all projects, in background."""
        projects: set[Project] = set()
        for column in self.query(Column):
            projects |= set(column.list_projects())
        self._fetch_projects(projects)

    def _scan(self, columns: list[Column], *, initial: bool) -> None:
        worker = get_current_worker()
        call = self.call_from_thread
        use_cache = initial and self._background_tasks
        try:
            # List projects (fast), deduplicating instances so that anything
            # cached on them (Repo objects, git call results) is shared by all columns.
            canonical: dict[Project, Project] = {}
            columns_by_project: dict[Project, list[Column]] = {}
            for column in columns:
                for project in column.list_projects():
                    project = canonical.setdefault(project, project)  # noqa: PLW2901
                    columns_by_project.setdefault(project, []).append(column)

            # Display data cached during the previous scan, if any:
            # the board is filled instantly, even on a cold disk cache.
            streaming = True
            if use_cache and (cached := cache._load(self._board_key)) is not None:
                projects_by_path = {str(project.path): project for project in columns_by_project}
                cached_rows = {
                    column: cache._decode_rows(cached[str(index)], projects_by_path)
                    for index, column in enumerate(columns)
                    if str(index) in cached
                }
                if len(cached_rows) == len(columns):
                    call(self._show_cached_columns, cached_rows)
                    streaming = False

            if streaming:
                call(self._reset_columns, columns)

            # Scan projects: each project is handled entirely by one thread,
            # computing the rows of every column interested in it.
            results: dict[Column, list[tuple[Any, ...]]] = {column: [] for column in columns}

            def scan_project(project: Project) -> list[tuple[Column, list[tuple[Any, ...]]]]:
                rows_by_column = []
                for column in columns_by_project[project]:
                    try:
                        rows = column.populate_rows(project)
                    except Exception as error:  # noqa: BLE001
                        self.log.error(f"Could not scan {project}: {error}")  # noqa: TRY400
                        rows = []
                    if rows:
                        rows_by_column.append((column, rows))
                return rows_by_column

            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                futures = [pool.submit(scan_project, project) for project in columns_by_project]
                for future in as_completed(futures):
                    if worker.is_cancelled:
                        pool.shutdown(wait=False, cancel_futures=True)
                        return
                    for column, rows in future.result():
                        results[column].extend(rows)
                        if streaming:
                            call(column._extend, rows)

            if streaming:
                call(self._finalize_columns, columns)
            else:
                call(self._refresh_columns, results)

            if use_cache:
                cache._save(self._board_key, {str(index): results[column] for index, column in enumerate(columns)})
        finally:
            self._scanning = False

        if initial and self._background_tasks and not worker.is_cancelled:
            self._fetch_projects(set(columns_by_project))
            if not worker.is_cancelled:
                call(self.notify, "Fetched all remotes — press F5 to refresh", title="Devboard")

    def _fetch_projects(self, projects: Iterable[Project]) -> None:
        worker = get_current_worker()
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = [pool.submit(project.fetch) for project in projects]
            for future in as_completed(futures):
                if worker.is_cancelled:
                    pool.shutdown(wait=False, cancel_futures=True)
                    return
                future.result()

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

    def _refresh_columns(self, results: dict[Column, list[tuple[Any, ...]]]) -> None:
        for column, rows in results.items():
            column._reset()
            if rows:
                column._extend(rows)
            column._finalize()

    def _show_cached_columns(self, cached_rows: dict[Column, list[tuple[Any, ...]]]) -> None:
        for column, rows in cached_rows.items():
            column._reset()
            if rows:
                column._extend(rows)
                column._mark_cached()
            column._finalize()

    def _load_columns(self) -> Iterable[Column | type[Column]]:
        board: str | Path
        try:
            with self._config_file.open("rb") as config_file:
                config: dict[str, Any] = tomllib.load(config_file)
        except FileNotFoundError:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            self._config_file.write_text('board = "default"')
            config = {"board": "default"}
        if self._scan_workers is None:
            self._scan_workers = config.get("workers")
        board = config["board"] if self._board is None else self._board
        if isinstance(board, str):
            board_file = self._config_file.parent.joinpath(f"{board}.py")
            if not board_file.exists():
                if board == "default":
                    board_file.write_text(Path(__file__).parent.joinpath("default_board.py").read_text())
                else:
                    board_file = Path(board)
        else:
            board_file = board
        if not board_file.exists():
            raise ValueError(f"devboard: error: Unknown board '{board}'")
        self._board_key = str(board_file)
        module_path = "devboard.user_board"
        spec = spec_from_file_location(module_path, str(board_file))
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not get import spec from '{module_path}'")
        user_config = module_from_spec(spec)
        sys.modules[module_path] = user_config
        spec.loader.exec_module(user_config)
        return user_config.columns

    @staticmethod
    def _bindings_help(cls: type, *, search_up: bool = False) -> Iterator[str]:  # noqa: PLW0211
        bindings = getattr(cls, "BINDINGS", []) if search_up else cls.__dict__.get("BINDINGS", [])
        for binding in bindings:
            if isinstance(binding, tuple):
                binding = Binding(*binding)  # noqa: PLW2901
            keys = "`, `".join(key.strip().upper().replace("+", "-") for key in binding.key.split(","))
            yield f"- `{keys}`: {binding.description}"
