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

"""Tests for loading board definitions and settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from devboard import Column
from devboard._internal.loader import _load_board

if TYPE_CHECKING:
    from pathlib import Path


BOARD_SOURCE = """
from devboard import Column


class Work(Column):
    TITLE = "Work"


columns = [Work]
"""


def test_create_default_configuration_and_board(tmp_path: Path) -> None:
    """The first load creates a usable default configuration and board."""
    config_file = tmp_path / "devboard" / "config.toml"

    definition = _load_board(None, config_file=config_file)

    assert config_file.read_text(encoding="utf-8") == 'board = "default"\n'
    assert definition.path == (config_file.parent / "default.py").resolve()
    assert definition.columns


def test_load_named_board_and_settings(tmp_path: Path) -> None:
    """A named board is resolved next to its configuration file."""
    config_file = tmp_path / "devboard" / "config.toml"
    config_file.parent.mkdir()
    config_file.write_text('board = "work"\nworkers = 3\n', encoding="utf-8")
    board_file = config_file.parent / "work.py"
    board_file.write_text(BOARD_SOURCE, encoding="utf-8")

    definition = _load_board(None, config_file=config_file)

    assert definition.path == board_file.resolve()
    assert definition.workers == 3
    assert len(definition.columns) == 1
    column = definition.columns[0]
    assert isinstance(column, type)
    assert issubclass(column, Column)


def test_explicit_board_overrides_configured_board(tmp_path: Path) -> None:
    """An explicit board path takes precedence over the configured name."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('board = "missing"\n', encoding="utf-8")
    board_file = tmp_path / "selected.py"
    board_file.write_text(BOARD_SOURCE, encoding="utf-8")

    definition = _load_board(board_file, config_file=config_file)

    assert definition.path == board_file.resolve()


@pytest.mark.parametrize(
    ("workers", "error_type"),
    [(True, TypeError), ("many", TypeError), (0, ValueError), (-1, ValueError)],
)
def test_invalid_worker_count_is_rejected(
    tmp_path: Path,
    workers: object,
    error_type: type[Exception],
) -> None:
    """The worker count must be a positive integer."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(f'board = "work"\nworkers = {workers!r}\n'.lower(), encoding="utf-8")
    (tmp_path / "work.py").write_text(BOARD_SOURCE, encoding="utf-8")

    with pytest.raises(error_type, match="positive integer"):
        _load_board(None, config_file=config_file)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("value = 1\n", "iterable named 'columns'"),
        ("columns = [object()]\n", "Invalid column"),
    ],
)
def test_invalid_board_definition_is_rejected(tmp_path: Path, source: str, message: str) -> None:
    """A board must provide an iterable of column classes or instances."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('board = "work"\n', encoding="utf-8")
    (tmp_path / "work.py").write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        _load_board(None, config_file=config_file)
