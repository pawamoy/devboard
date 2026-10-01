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

from typing import TYPE_CHECKING, ClassVar

from textual import on
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult


class _FilterInput(ModalScreen[str | None]):
    """Read filter text, or return `None` when the user cancels."""

    BINDINGS: ClassVar = [Binding("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    _FilterInput {
        align: center middle;
    }

    _FilterInput > Vertical {
        width: 60;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }

    _FilterInput Label {
        margin-bottom: 1;
    }
    """

    def __init__(self, title: str, value: str = "") -> None:
        """Initialize the prompt with the current filter."""
        super().__init__()
        self._title = title
        self._value = value

    def compose(self) -> ComposeResult:
        """Show the scope and an input that also allows clearing the filter."""
        with Vertical():
            yield Label(self._title)
            yield Input(value=self._value, placeholder="Filter text (empty shows all rows)")

    @on(Input.Submitted)
    def _on_submitted(self, event: Input.Submitted) -> None:
        """Apply the submitted text to the chosen columns."""
        event.stop()
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        """Close the prompt without changing the filter."""
        self.dismiss(None)
