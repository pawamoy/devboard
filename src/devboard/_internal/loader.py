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

import hashlib
import sys
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import TYPE_CHECKING, Any

from appdirs import user_config_dir

from devboard._internal.board import Column

# TODO: Remove once support for Python 3.10 is dropped.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class _BoardDefinition:
    """A loaded board and the settings that affect it."""

    path: Path
    columns: tuple[Column | type[Column], ...]
    workers: int | None


def _config_file() -> Path:
    """Return the user configuration file."""
    return Path(user_config_dir(), "devboard", "config.toml")


def _load_board(board: str | Path | None, *, config_file: Path | None = None) -> _BoardDefinition:
    """Load and validate a board before the Textual widget tree is composed."""
    config_file = config_file or _config_file()
    config = _load_config(config_file)
    workers = _validate_workers(config.get("workers"), config_file)
    selected_board = config.get("board", "default") if board is None else board
    board_file = _resolve_board_file(selected_board, config_file)
    columns = _load_columns(board_file)
    return _BoardDefinition(path=board_file.resolve(), columns=columns, workers=workers)


def _load_config(config_file: Path) -> dict[str, Any]:
    """Read the user configuration, and create the default file if necessary."""
    try:
        with config_file.open("rb") as stream:
            config = tomllib.load(stream)
    except FileNotFoundError:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text('board = "default"\n', encoding="utf-8")
        return {"board": "default"}

    return config


def _validate_workers(value: Any, config_file: Path) -> int | None:
    """Validate the configured number of repository workers."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"devboard: error: 'workers' in '{config_file}' must be a positive integer")
    if value < 1:
        raise ValueError(f"devboard: error: 'workers' in '{config_file}' must be a positive integer")
    return value


def _resolve_board_file(board: Any, config_file: Path) -> Path:
    """Resolve a board name or path to an existing Python file."""
    if not isinstance(board, (str, Path)):
        raise TypeError("devboard: error: 'board' must be a name or file path")

    if isinstance(board, str):
        named_board = config_file.parent / f"{board}.py"
        if named_board.exists():
            board_file = named_board
        elif board == "default":
            board_file = named_board
            default_board = Path(__file__).parent / "default_board.py"
            board_file.write_text(default_board.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            board_file = Path(board)
    else:
        board_file = board

    if not board_file.exists():
        raise ValueError(f"devboard: error: Unknown board '{board}'")
    if not board_file.is_file():
        raise ValueError(f"devboard: error: Board '{board_file}' is not a file")
    return board_file


def _load_columns(board_file: Path) -> tuple[Column | type[Column], ...]:
    """Import a board module and return its validated columns."""
    digest = hashlib.sha256(str(board_file.resolve()).encode()).hexdigest()[:12]
    module_path = f"devboard.user_board_{digest}"
    spec = spec_from_file_location(module_path, board_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create an import spec for '{board_file}'")

    user_board = module_from_spec(spec)
    sys.modules[module_path] = user_board
    try:
        spec.loader.exec_module(user_board)
    except Exception:
        sys.modules.pop(module_path, None)
        raise

    try:
        columns: Iterable[Any] = user_board.columns
        loaded_columns = tuple(columns)
    except (AttributeError, TypeError) as error:
        raise ValueError(f"devboard: error: Board '{board_file}' must define an iterable named 'columns'") from error

    for column in loaded_columns:
        is_column = isinstance(column, Column) or (isinstance(column, type) and issubclass(column, Column))
        if not is_column:
            raise ValueError(f"devboard: error: Invalid column {column!r} in board '{board_file}'")
    return loaded_columns
