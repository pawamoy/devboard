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

"""Tests for application key bindings and help."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from rich.console import Console
from rich.markdown import Markdown
from textual.binding import Binding
from textual.command import CommandInput, CommandPalette
from textual.widgets import Footer, HelpPanel, Static
from textual.widgets._footer import FooterKey

from devboard import Board, Column, Devboard
from devboard._internal.modal import Modal
from tests.snapshot_app import ChangesColumn, SnapshotDevboard, UpdatesColumn


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


def _render_keys_panel(panel: HelpPanel) -> str:
    """Render the full bindings list without the panel's scroll position."""
    console = Console(width=120, color_system=None)
    with console.capture() as capture:
        console.print(panel.query_one("BindingsTable", Static).render())
    return capture.get()


def test_board_can_replace_help_and_exit_keys() -> None:
    """Only the board's keys open help and request exit."""

    async def run_test() -> None:
        app = CustomBindingsDevboard()
        async with app.run_test() as pilot:
            await pilot.pause()

            # Keys and Palette sit together at the right edge.
            footer = app.query_one(Footer)
            footer_keys = {key.action: key for key in footer.query(FooterKey)}

            assert set(footer_keys) == {"toggle_help_panel", "command_palette"}
            assert footer_keys["toggle_help_panel"].region.x > app.screen.region.x
            assert footer_keys["toggle_help_panel"].region.right == footer_keys["command_palette"].region.x
            assert footer_keys["command_palette"].region.right == footer.region.right

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


def test_board_bindings_keep_priority_tooltips_and_keymap_ids() -> None:
    """Installing board bindings preserves their behavior and display options."""
    actions: list[str] = []

    class EditableColumn(ChangesColumn):
        BINDINGS: ClassVar = [("e", "edit", "Column edit")]

        def action_edit(self) -> None:
            """Record that the column handled the edit key."""
            actions.append("column")

    class BindingsDevboard(SnapshotDevboard):
        def _load_board(self) -> Board:
            return Board(
                [EditableColumn()],
                bindings=[
                    Binding("e", "edit", "Board edit", priority=True, tooltip="Run the board action", id="board-edit"),
                    Binding("f10", "show_help", "Internal help", system=True),
                    ("?", "show_help", "Help"),
                ],
            )

        def action_edit(self) -> None:
            """Record that the board handled the edit key."""
            actions.append("board")

    async def run_test() -> None:
        app = BindingsDevboard()
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            app.query_one(EditableColumn).table.focus()

            # Priority lets the board handle a key also bound by the focused column.
            await pilot.press("e")

            assert actions == ["board"]

            # The Keys panel keeps tooltips and omits bindings marked as system actions.
            await pilot.press("ctrl+k")
            await pilot.pause()
            panel_text = _render_keys_panel(app.query_one(HelpPanel))

            assert "Board edit Run the board action" in panel_text
            assert "Internal help" not in panel_text
            assert "Column edit" not in panel_text

            # Binding IDs let a keymap move the board action and free the column's original key.
            app.set_keymap({"board-edit": "f9"})
            await pilot.press("e", "f9")

            assert actions == ["board", "column", "board"]

            # A literal punctuation key works without Textual's internal key name.
            await pilot.press("question_mark")

            assert isinstance(app.screen, Modal)

    asyncio.run(run_test())


def test_ctrl_k_toggles_keys_panel_with_column_actions_in_footer() -> None:
    """Column actions stay in the footer, and Ctrl+K shows all available keys."""

    class EditingColumn(ChangesColumn):
        BINDINGS: ClassVar = [Binding("e", "edit", "Open in editor")]

    class EditableColumn(EditingColumn):
        BINDINGS: ClassVar = [
            Binding("d", "diff", "Show diff", show=False),
            Binding("z", "internal", "Internal action", show=False, system=True),
        ]

    class StatusColumn(UpdatesColumn):
        BINDINGS: ClassVar = [("s", "status", "Project status")]

    class KeysDevboard(SnapshotDevboard):
        def _load_board(self) -> Board:
            return Board(
                [EditableColumn(), StatusColumn()],
                bindings=[
                    ("h", "show_help", "Help"),
                    ("x", "exit", "Exit"),
                    Binding("r,ctrl+r", "refresh_board", "Refresh board", key_display="R"),
                    ("f2", "force_refresh_board", "Force refresh board"),
                    ("f3", "app.refresh_column", "Refresh column"),
                    ("f4", "force_refresh_column", "Force refresh column"),
                    ("f5", "refresh_item", "Refresh item"),
                    ("f6", "force_refresh_item", "Force refresh item"),
                ],
            )

    async def run_test() -> None:
        app = KeysDevboard()
        async with app.run_test(size=(100, 24)) as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            editable_column = app.query_one(EditableColumn)
            editable_column.table.focus()
            await pilot.pause()

            # Visible column actions, Keys, and Palette form one row on the right.
            footer = app.query_one(Footer)
            footer_keys = {key.action: key for key in footer.query(FooterKey)}

            assert set(footer_keys) == {"edit", "toggle_help_panel", "command_palette"}
            assert footer_keys["edit"].region.x > app.screen.region.x
            assert footer_keys["edit"].region.right == footer_keys["toggle_help_panel"].region.x
            assert footer_keys["toggle_help_panel"].region.right == footer_keys["command_palette"].region.x
            assert footer_keys["command_palette"].region.right == footer.region.right
            assert not app.query(HelpPanel)

            await pilot.press("ctrl+k")
            await pilot.pause()

            panel = app.query_one(HelpPanel)
            panel_text = _render_keys_panel(panel)

            # The panel groups related actions across widgets and separates inherited movement keys.
            _, main_keys = panel_text.split("Main keys", maxsplit=1)
            main_keys, selection = main_keys.split("Selection", maxsplit=1)
            selection, columns = selection.split("Columns", maxsplit=1)
            columns, column_actions = columns.split("Column actions", maxsplit=1)
            column_actions, movement = column_actions.split("Movement", maxsplit=1)
            movement, other = movement.split("Other", maxsplit=1)
            sections = {
                "main": main_keys,
                "selection": selection,
                "columns": columns,
                "custom": column_actions,
                "movement": movement,
                "other": other,
            }
            expected = {
                "main": ("Keys", "Palette", "Help", "Exit"),
                "selection": (
                    "Toggle select",
                    "Toggle select all",
                    "Reverse selection",
                    "Expand selection up",
                    "Expand selection down",
                ),
                "columns": (
                    "Collapse/expand column",
                    "Maximize/unmaximize column",
                    "Refresh board",
                    "Force refresh board",
                    "Refresh column",
                    "Force refresh column",
                    "Refresh item",
                    "Force refresh item",
                ),
                "custom": ("Open in editor", "Show diff"),
                "movement": ("Cursor up", "Cursor down", "Page up", "Page down", "Focus Next", "Focus Previous"),
                "other": ("Copy selected text",),
            }

            for group, descriptions in expected.items():
                for description in descriptions:
                    assert description in sections[group]
                    assert all(
                        description not in text for other_group, text in sections.items() if other_group != group
                    )

            # Hidden footer actions remain visible, aliases share a row, and system bindings stay hidden.
            assert "Internal action" not in panel_text
            refresh_line = next(line for line in columns.splitlines() if "Refresh board" in line)
            assert refresh_line.strip() == "R Refresh board"

            # Both the footer and the open panel follow focus to another column.
            app.query_one(StatusColumn).table.focus()
            await pilot.pause()

            footer_keys = {key.action: key for key in footer.query(FooterKey)}

            assert set(footer_keys) == {"status", "toggle_help_panel", "command_palette"}
            assert footer_keys["status"].region.right == footer_keys["toggle_help_panel"].region.x
            assert footer_keys["toggle_help_panel"].region.right == footer_keys["command_palette"].region.x
            assert footer_keys["command_palette"].region.right == footer.region.right
            panel_text = _render_keys_panel(panel)
            column_actions = panel_text.split("Column actions", maxsplit=1)[1].split("Movement", maxsplit=1)[0]

            assert "Project status" in column_actions
            assert "Open in editor" not in panel_text

            await pilot.press("ctrl+k")
            await pilot.pause()

            assert not app.query(HelpPanel)

    asyncio.run(run_test())


def test_palette_keys_command_opens_grouped_panel() -> None:
    """The palette's Keys command uses the same groups and skips empty sections."""

    async def run_test() -> None:
        app = CustomBindingsDevboard()
        async with app.run_test() as pilot:
            await pilot.press("ctrl+p")
            palette = app.screen
            assert isinstance(palette, CommandPalette)

            palette.query_one(CommandInput).value = "Keys"
            await pilot.pause()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.press("enter")
            await pilot.pause()

            # A board without columns has no selection or column sections.
            panel_text = _render_keys_panel(app.query_one(HelpPanel))

            assert "Main keys" in panel_text
            for description in ("Keys", "Palette", "Help", "Exit"):
                assert description in panel_text
            for group in ("Selection", "Columns", "Column actions"):
                assert group not in panel_text

            await pilot.press("ctrl+k")

            assert not app.query(HelpPanel)

    asyncio.run(run_test())


def test_help_includes_inherited_column_bindings() -> None:
    """Help shows inherited actions and respects binding overrides and opt-outs."""

    class SharedColumn(Column):
        BINDINGS: ClassVar = [Binding("e", "edit", "Open in Zed")]

    class ProjectsColumn(SharedColumn):
        TITLE = "Projects"
        BINDINGS: ClassVar = [("s", "status", "Project status")]

    class TerminalColumn(SharedColumn):
        TITLE = "Terminal"
        BINDINGS: ClassVar = [("e", "terminal", "Open in terminal")]

    class IndependentColumn(SharedColumn, inherit_bindings=False):
        TITLE = "Independent"
        BINDINGS: ClassVar = [("i", "inspect", "Inspect item")]

    class HelpDevboard(CustomBindingsDevboard):
        def _load_board(self) -> Board:
            return Board(
                [ProjectsColumn, TerminalColumn, IndependentColumn],
                bindings=[("h", "show_help", "Help")],
            )

    async def run_test() -> None:
        # Each column uses the shared binding differently.
        app = HelpDevboard()
        async with app.run_test() as pilot:
            await pilot.press("h")
            await pilot.pause()

            assert isinstance(app.screen, Modal)
            content = app.screen.query_one(Static).content
            assert isinstance(content, Markdown)

            main_help, columns_help = content.markup.split("## Selection\n", maxsplit=1)
            selection_help, columns_help = columns_help.split("## Columns\n", maxsplit=1)
            common_columns_help, columns_help = columns_help.split("## Current board\n", maxsplit=1)
            _, columns_help = columns_help.split("### Projects\n", maxsplit=1)
            projects_help, columns_help = columns_help.split("### Terminal\n", maxsplit=1)
            terminal_help, independent_help = columns_help.split("### Independent\n", maxsplit=1)

            # Main keys and selection actions have separate sections.
            assert "## Main keys" in main_help
            assert ": Help" in main_help
            assert ": Keys" in main_help
            assert "Toggle select" in selection_help
            assert "Toggle select" not in main_help

            # The shared action appears alongside the project's own action.
            assert "Open in Zed" in projects_help
            assert "Project status" in projects_help

            # Overrides and disabled inheritance must not advertise the base action.
            assert "Open in terminal" in terminal_help
            assert "Open in Zed" not in terminal_help
            assert "Inspect item" in independent_help
            assert "Open in Zed" not in independent_help

            # Common column controls have one section before the individual columns.
            assert "Collapse/expand column" in common_columns_help
            assert "Maximize/unmaximize column" in common_columns_help
            assert "Collapse/expand column" not in main_help
            assert "Collapse/expand column" not in selection_help
            assert "Collapse/expand column" not in projects_help
            assert "Collapse/expand column" not in terminal_help

    asyncio.run(run_test())
