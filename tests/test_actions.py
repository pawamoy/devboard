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
from threading import get_ident
from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from textual import on
from textual.app import App
from textual.screen import ModalScreen
from textual.widgets import Input

from devboard import Column, Project, Row, row_action, rows_action
from devboard._internal.default_board import ToPull

if TYPE_CHECKING:
    from pathlib import Path

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
    def action_base(self, row: Row[str], /) -> None:
        """Record the inherited action."""
        self.actions.append(("base", row.item))


class ExtendedActionsColumn(BaseActionsColumn):
    """Add an action without replacing the base action."""

    BINDINGS: ClassVar = [("e", "extra", "Extra action")]

    @row_action
    def action_extra(self, row: Row[str], /) -> None:
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


class BatchActionsColumn(Column[str]):
    """Record the rows and execution thread received by a batch action."""

    HEADERS = ("Value",)
    BINDINGS: ClassVar = [("b", "batch", "Batch action")]

    def __init__(self) -> None:
        """Initialize batch history."""
        super().__init__()
        self.batches: list[list[Row[str]]] = []
        self.action_thread: int | None = None

    @rows_action
    def action_batch(self, rows: list[Row[str]], /) -> None:
        """Record the entire batch and remove its rows."""
        self.action_thread = get_ident()
        self.batches.append(rows)
        for row in rows:
            row.remove()


@pytest.mark.parametrize("threaded", [True, False], ids=["threaded", "foreground"])
@pytest.mark.parametrize("selection", ["selected", "current", "empty", "filtered"])
def test_rows_action_receives_one_visible_batch(selection: str, threaded: bool) -> None:
    """Batch actions use visible selections, fall back to the cursor, and skip empty tables."""

    async def run_test() -> None:
        column = BatchActionsColumn()
        column.THREADED = threaded
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            if selection != "empty":
                for value in ("first", "second", "third"):
                    column._extend_item(value, [(value,)])
            column._finalize()

            # Leave the cursor on an unselected row to distinguish selection from fallback.
            if selection in {"selected", "filtered"}:
                for row in list(column.table.selectable_rows)[1:]:
                    row.select()
            if selection == "filtered":
                column.filter_rows(lambda row: row.item != "second")

            await pilot.press("b")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()

            expected = {"selected": ["second", "third"], "current": ["first"], "empty": [], "filtered": ["third"]}[
                selection
            ]
            assert len(column.batches) == bool(expected)
            if expected:
                # Snapshots retain source items and cells after the displayed rows are removed.
                assert [row.item for row in column.batches[0]] == expected
                assert [row.data for row in column.batches[0]] == [[value] for value in expected]
                assert (column.action_thread != get_ident()) == threaded
            remaining = {"selected": 1, "current": 2, "empty": 0, "filtered": 1}[selection]
            assert column.table.row_count == remaining

            if selection == "filtered":
                # Clearing the filter restores the selected row excluded from the batch.
                column.filter_rows(None)
                assert [row.item for row in column.table.selectable_rows] == ["first", "second"]
                assert [row.item for row in column.table.selected_rows] == ["second"]

    asyncio.run(run_test())


@pytest.mark.parametrize("batch", [True, False], ids=["rows_action", "row_action"])
@pytest.mark.parametrize("asynchronous", [True, False], ids=["async", "sync"])
@pytest.mark.parametrize("threaded", [True, False], ids=["threaded", "foreground"])
@pytest.mark.parametrize("selected", [True, False], ids=["selected", "current"])
def test_row_actions_forward_binding_arguments(batch: bool, asynchronous: bool, threaded: bool, selected: bool) -> None:
    """Binding arguments follow the positional-only row or row list for sync and async callbacks."""

    class ParameterActionsColumn(Column[str]):
        """Record arguments, source items, and the callback's execution thread."""

        HEADERS = ("Value",)
        BINDINGS: ClassVar = [
            ("r", "label_row('feature', 7)", "Label row"),
            ("b", "label_batch('feature', 7)", "Label batch"),
            ("a", "label_async_row('feature', 7)", "Label row asynchronously"),
            ("s", "label_async_batch('feature', 7)", "Label batch asynchronously"),
        ]

        def __init__(self) -> None:
            """Initialize callback history."""
            super().__init__()
            self.calls: list[tuple[str, int, list[str], int]] = []

        @row_action
        def action_label_row(self, row: Row[str], /, label: str, count: int) -> None:
            """Record arguments for one row."""
            self.calls.append((label, count, [row.item], get_ident()))

        @rows_action
        def action_label_batch(self, rows: list[Row[str]], /, label: str, count: int) -> None:
            """Record arguments for the entire batch."""
            self.calls.append((label, count, [row.item for row in rows], get_ident()))

        @row_action
        async def action_label_async_row(self, row: Row[str], /, label: str, count: int) -> None:
            """Record arguments for one row after yielding."""
            await asyncio.sleep(0)
            self.calls.append((label, count, [row.item], get_ident()))

        @rows_action
        async def action_label_async_batch(self, rows: list[Row[str]], /, label: str, count: int) -> None:
            """Record arguments for the entire batch after yielding."""
            await asyncio.sleep(0)
            self.calls.append((label, count, [row.item for row in rows], get_ident()))

    async def run_test() -> None:
        column = ParameterActionsColumn()
        column.THREADED = threaded
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            for value in ("first", "second", "third"):
                column._extend_item(value, [(value,)])
            column._finalize()

            # Keep the cursor outside the selection to distinguish both dispatch paths.
            if selected:
                for row in list(column.table.selectable_rows)[1:]:
                    row.select()

            key = {(False, False): "r", (True, False): "b", (False, True): "a", (True, True): "s"}[batch, asynchronous]
            await pilot.press(key)
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()

            expected_items = ["second", "third"] if selected else ["first"]
            expected_calls = [expected_items] if batch else [[item] for item in expected_items]
            assert sorted((label, count, items) for label, count, items, _ in column.calls) == [
                ("feature", 7, items) for items in expected_calls
            ]
            assert all((thread != get_ident()) == (threaded and not asynchronous) for _, _, _, thread in column.calls)

    asyncio.run(run_test())


@pytest.mark.parametrize("batch", [True, False], ids=["rows_action", "row_action"])
def test_binding_keywords_do_not_replace_positional_rows(batch: bool) -> None:
    """Binding keywords named row or rows remain separate from the supplied snapshots."""

    class KeywordActionsColumn(Column[str]):
        """Record source items and binding keyword arguments."""

        HEADERS = ("Value",)
        THREADED = False

        def __init__(self) -> None:
            """Initialize callback history."""
            super().__init__()
            self.calls: list[tuple[list[str], dict[str, str]]] = []

        @row_action
        def action_record_row(self, row: Row[str], /, **kwargs: str) -> None:
            """Record one positional row and its separate binding keywords."""
            self.calls.append(([row.item], kwargs))

        @rows_action
        def action_record_batch(self, rows: list[Row[str]], /, **kwargs: str) -> None:
            """Record positional rows and their separate binding keywords."""
            self.calls.append(([row.item for row in rows], kwargs))

    async def run_test() -> None:
        column = KeywordActionsColumn()
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            column._extend_item("issue", [("Issue",)])
            column._finalize()

            # Names used by the injected row parameters can also appear in binding keywords.
            action = column.action_record_batch if batch else column.action_record_row
            action(row="row keyword", rows="rows keyword")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()

            assert column.calls == [(["issue"], {"row": "row keyword", "rows": "rows keyword"})]

    asyncio.run(run_test())


class BatchMessage(ModalScreen[str | None]):
    """Ask for one message shared by the batch."""

    BINDINGS: ClassVar = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        """Show a message input."""
        yield Input()

    @on(Input.Submitted)
    def _submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_cancel(self) -> None:
        """Cancel the batch prompt."""
        self.dismiss(None)


class PromptBatchColumn(BatchActionsColumn):
    """Apply one prompted message to every row in an async batch."""

    def __init__(self) -> None:
        """Initialize prompted operation history."""
        super().__init__()
        self.messages: list[tuple[str, str]] = []
        self.prompts = 0

    @rows_action
    async def action_batch(self, rows: list[Row[str]], /) -> None:
        """Prompt once and record the same message for each row."""
        self.prompts += 1
        message = await self.app.push_screen_wait(BatchMessage())
        if message is None:
            return
        for row in rows:
            await asyncio.to_thread(self.messages.append, (row.item, message))
            row.remove()


@pytest.mark.parametrize("threaded", [True, False], ids=["threaded", "foreground"])
@pytest.mark.parametrize("cancel", [True, False], ids=["cancel", "submit"])
def test_async_rows_action_prompts_once_for_shared_input(threaded: bool, cancel: bool) -> None:
    """An async worker can prompt once and either apply shared input or cancel the whole batch."""

    async def run_test() -> None:
        column = PromptBatchColumn()
        column.THREADED = threaded
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            for value in ("first", "second"):
                column._extend_item(value, [(value,)])
            column._finalize()
            for row in column.table.selectable_rows:
                row.select()

            await pilot.press("b")
            await pilot.pause()

            assert isinstance(app.screen, BatchMessage)
            if cancel:
                await pilot.press("escape")
            else:
                app.screen.query_one(Input).value = "Shared message"
                await pilot.press("enter")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()

            assert column.prompts == 1
            assert column.messages == ([] if cancel else [("first", "Shared message"), ("second", "Shared message")])
            assert column.table.row_count == (2 if cancel else 0)

    asyncio.run(run_test())


@pytest.mark.parametrize("threaded", [True, False], ids=["threaded", "foreground"])
def test_async_row_action_awaits_each_selected_row(threaded: bool) -> None:
    """Single-row and batch decorators both support asynchronous callbacks."""

    class AsyncColumn(BatchActionsColumn):
        @row_action
        async def action_record(self, row: Row[str], /) -> None:
            """Record a row after yielding to the event loop."""
            await asyncio.sleep(0)
            self.batches.append([row])
            row.remove()

    async def run_test() -> None:
        column = AsyncColumn()
        column.THREADED = threaded
        app = ActionApp(column)
        async with app.run_test() as pilot:
            column._reset()
            for value in ("first", "second"):
                column._extend_item(value, [(value,)])
            column._finalize()
            for row in column.table.selectable_rows:
                row.select()

            column.action_record()
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            await pilot.pause()

            assert sorted(batch[0].item for batch in column.batches) == ["first", "second"]
            assert column.table.row_count == 0

    asyncio.run(run_test())
