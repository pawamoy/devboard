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

from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import App, ComposeResult
    from textual.events import Key


class Modal(ModalScreen):
    """A modal screen."""

    def __init__(self, *args: Any, text: Any, **kwargs: Any) -> None:
        """Initialize the screen."""
        super().__init__(*args, **kwargs)
        if isinstance(text, str):
            self.text = Text.from_ansi(text)
            """Text content."""
        else:
            self.text = text

    def compose(self) -> ComposeResult:
        """Screen composition."""
        yield VerticalScroll(Static(self.text), id="modal-contents")

    def on_key(self, event: Key) -> None:
        """Dismiss on any unbound key."""
        if not any(bindings.keys.get(event.key) for _, bindings in self.app._modal_binding_chain):  # type: ignore[attr-defined]
            self.dismiss()


class ModalMixin:
    """Mixin class to add a modal method."""

    app: App
    """Textual application."""

    def modal(self, text: str) -> None:
        """Push a modal."""
        self.app.push_screen(Modal(text=text))
