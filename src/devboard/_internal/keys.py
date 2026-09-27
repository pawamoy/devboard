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

from typing import TYPE_CHECKING

from rich import box
from rich.table import Table
from rich.text import Text
from textual.binding import Binding
from textual.widgets import DataTable, HelpPanel, KeyPanel, Markdown
from textual.widgets._key_panel import BindingsTable

from devboard._internal.board import Column
from devboard._internal.datatable import SelectableRowsDataTable

if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.dom import DOMNode

_REFRESH_COMMANDS = {
    "refresh_board": ("Refresh board", "Scan all columns"),
    "force_refresh_board": ("Force refresh board", "Update all items before scanning every column"),
    "refresh_column": ("Refresh column", "Scan the focused column"),
    "force_refresh_column": ("Force refresh column", "Update items before scanning the focused column"),
    "refresh_item": ("Refresh item", "Scan the item under the cursor in every column that lists it"),
    "force_refresh_item": ("Force refresh item", "Update the item under the cursor before scanning it across columns"),
}

_MAIN_ACTIONS = {
    "toggle_help_panel",
    "show_help_panel",
    "hide_help_panel",
    "command_palette",
    "show_help",
    "exit",
    "quit",
}
_SELECTION_ACTIONS = {binding.action for binding in Binding.make_bindings(SelectableRowsDataTable.BINDINGS)}
_COLUMN_ACTIONS = {
    *(binding.action for binding in Binding.make_bindings(Column.BINDINGS)),
    *_REFRESH_COMMANDS,
}


def _binding_group(node: DOMNode, binding: Binding) -> str:
    """Group related actions even when different widgets own their bindings."""
    action = binding.action.removeprefix("app.")
    if action in _MAIN_ACTIONS:
        return "Main keys"
    if action in _SELECTION_ACTIONS:
        return "Selection"
    if action in _COLUMN_ACTIONS:
        return "Columns"
    if isinstance(node, Column):
        return "Column actions"
    if isinstance(node, DataTable) or action in {"focus_next", "focus_previous"}:
        return "Movement"
    return node.BINDING_GROUP_TITLE or "Other"


class _GroupedBindingsTable(BindingsTable):
    """Display active bindings in sections by purpose."""

    def render_bindings_table(self) -> Table:
        """Keep aliases together within each section and omit system bindings."""
        groups: dict[str, dict[tuple[DOMNode, str], list[Binding]]] = {
            title: {} for title in ("Main keys", "Selection", "Columns", "Column actions", "Movement")
        }
        for node, binding, _enabled, _tooltip in self.screen.active_bindings.values():
            if binding.system:
                continue
            actions = groups.setdefault(_binding_group(node, binding), {})
            actions.setdefault((node, binding.action), []).append(binding)

        key_style = self.get_component_rich_style("bindings-table--key")
        description_style = self.get_component_rich_style("bindings-table--description")
        header_style = self.get_component_rich_style("bindings-table--header")
        divider_transparent = self.get_component_styles("bindings-table--divider").color.a == 0
        table = Table(
            padding=(0, 0),
            show_header=False,
            box=box.SIMPLE if divider_transparent else box.HORIZONTALS,
            border_style=self.get_component_rich_style("bindings-table--divider"),
        )
        table.add_column("", justify="right")
        table.add_column("")

        for title, actions in groups.items():
            if not actions:
                continue
            table.add_row("", Text(title, style=header_style))
            for bindings in actions.values():
                binding = bindings[0]
                keys = " ".join(dict.fromkeys(self.app.get_key_display(alias) for alias in bindings))
                description = Text.from_markup(binding.description, style=description_style)
                if binding.tooltip:
                    if binding.description:
                        description.append(" ")
                    description.append(binding.tooltip, "dim")
                table.add_row(Text(keys, style=key_style), description)
            table.add_section()

        return table


class _GroupedKeyPanel(KeyPanel):
    """Keep grouped bindings up to date when focus changes."""

    def compose(self) -> ComposeResult:
        """Use the grouped table inside Textual's scrolling keys panel."""
        yield _GroupedBindingsTable(shrink=True, expand=False)


class _KeysPanel(HelpPanel):
    """Show widget help with Devboard's binding groups."""

    def compose(self) -> ComposeResult:
        """Keep widget help above the grouped bindings."""
        yield Markdown(id="widget-help")
        yield _GroupedKeyPanel(id="keys-help")
