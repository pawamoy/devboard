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

"""Tests for modal screens."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from devboard._internal.modal import Modal


class EscapeApp(App[None]):
    """Test app with the same application-level Escape binding as Devboard."""

    BINDINGS: ClassVar = [Binding("escape", "exit", "Exit")]

    def __init__(self) -> None:
        """Initialize the test app."""
        super().__init__()
        self.exit_requested = False

    def compose(self) -> ComposeResult:
        """Compose the test app."""
        yield Static("Main screen")

    def action_exit(self) -> None:
        """Record attempts to invoke the application-level exit action."""
        self.exit_requested = True


def test_escape_dismisses_modal_without_exiting_app() -> None:
    """Escape is consumed by an open modal before application bindings run."""

    async def run_test() -> None:
        app = EscapeApp()
        async with app.run_test() as pilot:
            app.push_screen(Modal(text="Modal contents"))
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            assert not isinstance(app.screen, Modal)
            assert not app.exit_requested

    asyncio.run(run_test())
