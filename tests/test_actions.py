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

"""Tests for column actions."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App

from devboard import Column, Project, Row, row_action
from devboard._internal.default_board import ToPull

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from textual.app import ComposeResult


class ActionApp(App[None]):
    """A small host for one actionable column."""

    def __init__(self, column: Column[Any]) -> None:
        """Initialize the host with its column."""
        super().__init__()
        self.column = column

    def compose(self) -> ComposeResult:
        """Compose the test application."""
        yield self.column


def test_delete_action_deletes_branch_and_removes_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The delete binding does not accidentally pull the selected branch."""
    project = Project(tmp_path)
    deleted: list[str] = []
    pulled: list[str | None] = []
    monkeypatch.setattr(Project, "delete", lambda self, branch: deleted.append(branch))
    monkeypatch.setattr(Project, "pull", lambda self, branch=None: pulled.append(branch))

    async def run_test() -> None:
        column = ToPull()
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            column._extend([(project, "merged", 2)])
            column._finalize()

            column.action_delete()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()

            assert deleted == ["merged"]
            assert pulled == []
            assert column.table.row_count == 0

    asyncio.run(run_test())

    assert project.lock()
    project.unlock()


class BaseActionsColumn(Column[str]):
    """A column with an action that subclasses inherit."""

    TITLE = "Actions"
    HEADERS = ("Item",)
    THREADED = False
    BINDINGS: ClassVar = [("b", "base", "Base action")]

    def __init__(self) -> None:
        """Initialize the action history."""
        super().__init__()
        self.actions: list[tuple[str, str]] = []

    @row_action
    def action_base(self, row: Row[str]) -> None:
        """Record the inherited action."""
        self.actions.append(("base", row.item))


class ExtendedActionsColumn(BaseActionsColumn):
    """Add an action without replacing the base action."""

    BINDINGS: ClassVar = [("e", "extra", "Extra action")]

    @row_action
    def action_extra(self, row: Row[str]) -> None:
        """Record the additional action."""
        self.actions.append(("extra", row.item))


def test_subclass_adds_row_action_without_replacing_base_action() -> None:
    """Inherited and additional bindings dispatch to their own row actions."""

    async def run_test() -> None:
        column = ExtendedActionsColumn()
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            column._extend_item("issue", [("Issue",)])
            column._finalize()

            await pilot.press("b")
            await pilot.press("e")
            await pilot.pause()

            assert column.actions == [("base", "issue"), ("extra", "issue")]

    asyncio.run(run_test())
