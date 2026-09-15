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

"""Visual regression tests for the terminal layout."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from devboard import Column
from tests.snapshot_app import SnapshotDevboard

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.pilot import Pilot


@pytest.fixture(autouse=True)
def _use_stable_color_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep snapshots independent of the developer's terminal color settings."""
    monkeypatch.delenv("NO_COLOR", raising=False)


async def _prepare_board(pilot: Pilot) -> None:
    """Wait for deterministic data and focus the first table."""
    await pilot.pause()
    await asyncio.wait_for(pilot.app.workers.wait_for_complete(), timeout=5)
    first_column = next(iter(pilot.app.query(Column)))
    pilot.app.set_focus(first_column.table)
    await pilot.hover("#task-progress")
    await pilot.pause()


async def _prepare_collapsed_board(pilot: Pilot) -> None:
    """Prepare the board, collapse the first column, and settle the mouse."""
    await _prepare_board(pilot)
    await pilot.press("c")
    await pilot.pause()
    await pilot.hover("#task-progress")
    await pilot.pause()


def test_populated_board_layout(snap_compare: Callable[..., bool]) -> None:
    """The populated two-column board keeps its visual structure."""
    assert snap_compare(SnapshotDevboard(), terminal_size=(100, 24), run_before=_prepare_board)


def test_collapsed_column_layout(snap_compare: Callable[..., bool]) -> None:
    """A collapsed focused column keeps its compact visual structure."""
    assert snap_compare(
        SnapshotDevboard(),
        terminal_size=(100, 24),
        run_before=_prepare_collapsed_board,
    )
