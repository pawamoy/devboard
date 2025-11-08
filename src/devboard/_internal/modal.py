"""Modal screen."""

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

    def modal(self, text: str) -> None:
        """Push a modal."""
        self.app.push_screen(Modal(text=text))
