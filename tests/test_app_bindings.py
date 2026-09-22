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

"""Tests for board-owned application key bindings."""

from __future__ import annotations

import asyncio

from devboard import Board, Devboard
from devboard._internal.modal import Modal


class CustomBindingsDevboard(Devboard):
    """Run a board with different help and exit keys."""

    def __init__(self) -> None:
        """Create the board without background work."""
        super().__init__(background_tasks=False)
        self.exit_requested = False

    def _load_board(self) -> Board:
        """Return a board that assigns help and exit to custom keys."""
        return Board([], bindings=[("h", "show_help", "Help"), ("x", "exit", "Exit")])

    def action_exit(self) -> None:
        """Record exit requests so the test can keep using the app."""
        self.exit_requested = True


def test_board_can_replace_help_and_exit_keys() -> None:
    """Only the board's keys open help and request exit."""

    async def run_test() -> None:
        app = CustomBindingsDevboard()
        async with app.run_test() as pilot:
            # The original keys and Textual's inherited quit key do nothing.
            await pilot.press("question_mark", "q", "ctrl+q")

            assert not isinstance(app.screen, Modal)
            assert not app.exit_requested

            # The custom keys invoke Devboard's existing actions.
            await pilot.press("h")
            await pilot.pause()

            assert isinstance(app.screen, Modal)

            await pilot.press("escape", "x")
            await pilot.pause()

            assert not isinstance(app.screen, Modal)
            assert app.exit_requested

    asyncio.run(run_test())
