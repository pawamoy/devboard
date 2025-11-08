"""The Textual application."""

from __future__ import annotations

import os
import sys
from importlib.util import module_from_spec, spec_from_file_location
from multiprocessing import Pool
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from appdirs import user_config_dir
from rich.markdown import Markdown
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from devboard._internal.board import Column, DataTable
from devboard._internal.modal import Modal, ModalMixin

# TODO: Remove once support for Python 3.10 is dropped.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

DEBUG = os.getenv("DEBUG", "0") == "1"


class Devboard(App, ModalMixin):
    """The Devboard application."""

    CSS_PATH = Path(__file__).parent / "devboard.tcss"
    BINDINGS: ClassVar = [
        Binding("F5, ctrl+r", "refresh", "Refresh"),
        Binding("question_mark", "show_help", "Help"),
        Binding("ctrl+q, q, escape", "exit", "Exit", key_display="Q"),
    ]

    # --------------------------------------------------
    # Textual methods.
    # --------------------------------------------------
    def __init__(
        self,
        *args: Any,
        board: str | Path | None = None,
        background_tasks: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the app."""
        super().__init__(*args, **kwargs)
        self._board = board
        self._config_file = Path(user_config_dir(), "devboard", "config.toml")
        self._background_tasks = background_tasks

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        for column in self._load_columns():
            if isinstance(column, Column):
                yield column
            else:
                yield column()
        yield Footer()

    def on_mount(self) -> None:
        """Run background tasks."""
        if self._background_tasks:
            self.fetch_all()

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
        for column in self.query(Column):
            column.update()

    def action_exit(self) -> None:
        """Exit application."""
        self.workers.cancel_all()
        self.exit()

    # --------------------------------------------------
    # Additional methods/properties.
    # --------------------------------------------------
    @work(thread=True)
    def fetch_all(self) -> None:
        """Run `git fetch` in all projects, in background."""
        projects = set()
        for column in self.query(Column):
            projects |= set(column.list_projects())
        with Pool() as pool:
            for project in projects:
                pool.apply_async(project.fetch)

    def _load_columns(self) -> Iterable[Column | type[Column]]:
        board: str | Path
        if self._board is None:
            try:
                with self._config_file.open("rb") as config_file:
                    config = tomllib.load(config_file)
            except FileNotFoundError:
                self._config_file.parent.mkdir(parents=True, exist_ok=True)
                self._config_file.write_text('board = "default"')
                board = "default"
            else:
                board = config["board"]
        else:
            board = self._board
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
        bindings = cls.BINDINGS if search_up else cls.__dict__.get("BINDINGS", [])  # type: ignore[attr-defined]
        for binding in bindings:
            if isinstance(binding, tuple):
                binding = Binding(*binding)  # noqa: PLW2901
            keys = "`, `".join(key.strip().upper().replace("+", "-") for key in binding.key.split(","))
            yield f"- `{keys}`: {binding.description}"
