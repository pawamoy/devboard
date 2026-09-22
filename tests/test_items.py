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

"""Tests for using arbitrary item types in board columns."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from threading import Event
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from rich.text import Text
from textual.widgets import Static

from devboard import Board, Column, Devboard, Project, Row, row_action
from devboard._internal import cache

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    import pytest


@dataclass
class Issue:
    """Small provider-specific issue model used by the test board."""

    repository: str
    number: int
    title: str

    def __str__(self) -> str:
        return f"{self.repository}#{self.number}"


class IssuesColumn(Column[Issue]):
    """Show issues without storing issue objects in display cells."""

    HEADERS = ("Title",)
    THREADED = False

    def __init__(self, issues: list[Issue]) -> None:
        """Initialize the column with issues returned by a provider."""
        super().__init__()
        self.issues = issues
        self.applied: list[Issue] = []

    def list_items(self) -> Iterator[Issue]:
        """List issues for this column."""
        yield from self.issues

    def item_key(self, issue: Issue) -> tuple[str, int]:
        """Identify an issue across provider responses and columns."""
        return issue.repository, issue.number

    def populate_rows(self, issue: Issue) -> list[tuple[Any, ...]]:
        """Display the title rather than the issue object."""
        return [(issue.title,)]

    @row_action
    def action_record(self, row: Row[Issue]) -> None:
        """Record the typed source item received by an action."""
        self.applied.append(row.item)


class ProjectsColumn(Column[Project]):
    """Show projects beside issues on the same board."""

    HEADERS = ("Name",)

    def __init__(self, project: Project) -> None:
        """Initialize the column with one project."""
        super().__init__()
        self.project = project

    def list_items(self) -> Iterator[Project]:
        """List the project for this column."""
        yield self.project

    def populate_rows(self, project: Project) -> list[tuple[str]]:
        """Display the project name."""
        return [(project.name,)]


class OrderedIssuesColumn(IssuesColumn):
    """Keep provider order while issue scans finish out of order."""

    def __init__(self, issues: list[Issue]) -> None:
        """Initialize synchronization events for every issue."""
        super().__init__(issues)
        self.started = {issue.number: Event() for issue in issues}
        self.release = {issue.number: Event() for issue in issues}

    def populate_rows(self, issue: Issue) -> list[tuple[Any, ...]]:
        """Wait until the test allows this issue to finish scanning."""
        self.started[issue.number].set()
        assert self.release[issue.number].wait(5)
        return super().populate_rows(issue)

    def _extend(self, rows: Iterable[tuple[Any, ...]]) -> None:
        """Add rows without sorting over the provider's order."""
        self.table.loading = False
        self.table.add_rows(rows)


def test_issue_and_project_columns_share_typed_source_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rows retain their source items when a board mixes item types."""
    canonical_issue = Issue("org/repo", 17, "Make the board generic")
    equivalent_issue = Issue("org/repo", 17, "A stale copy")
    issue_columns = [IssuesColumn([canonical_issue]), IssuesColumn([equivalent_issue])]
    project = Project(tmp_path / "devboard")
    project_column = ProjectsColumn(project)
    columns = [*issue_columns, project_column]
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board(columns))

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False)
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            for column in issue_columns:
                row = column.table.current_row
                assert row.data == ["Make the board generic"]
                assert row.item is canonical_issue

                column.action_record()
                assert column.applied == [canonical_issue]

            project_row = project_column.table.current_row
            assert project_row.data == ["devboard"]
            assert project_row.item is project

    asyncio.run(run_test())


def test_issue_rows_restore_current_items_from_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cached display cells reconnect to issue objects from the current scan."""
    cached_issue = Issue("org/repo", 17, "Cached title")
    cached_column = IssuesColumn([cached_issue])
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([cached_column]))

    async def run_test() -> None:
        previous_app = Devboard(board="test-board")
        async with previous_app.run_test():
            await asyncio.wait_for(previous_app.workers.wait_for_complete(), timeout=5)

        cached = cache._load("test-board")
        assert cached == {
            "0": [
                {
                    "item": ["org/repo", 17],
                    "cells": ["Cached title"],
                },
            ],
        }

        current_issue = Issue("org/repo", 17, "Current title")
        current_column = IssuesColumn([current_issue])
        monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([current_column]))
        app = Devboard(board="test-board")
        show_cached = Mock(wraps=app._show_cached_columns)
        monkeypatch.setattr(app, "_show_cached_columns", show_cached)
        async with app.run_test():
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            cached_rows = show_cached.call_args.args[0][current_column]
            assert cached_rows == [(current_issue, ("Cached title",))]
            assert current_column.table.current_row.data == ["Current title"]
            assert current_column.table.current_row.item is current_issue

    asyncio.run(run_test())


def test_refresh_lists_backlog_items_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """A normal board refresh discovers issues added by the provider."""
    issues = [Issue("org/repo", 1, "First")]
    column = IssuesColumn(issues)
    board = Board([column], bindings=[("ctrl+r", "refresh", "Refresh")])
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False)
        async with app.run_test() as pilot:
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            issues.append(Issue("org/repo", 2, "Second"))
            await pilot.press("ctrl+r")
            await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

            assert [row.item.number for row in column.table.selectable_rows] == [1, 2]

    asyncio.run(run_test())


def test_issue_rows_keep_provider_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """A later item waits for earlier item results before it reaches the table."""
    issues = [Issue("org/repo", 1, "First"), Issue("org/repo", 2, "Second")]
    column = OrderedIssuesColumn(issues)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False, workers=2)
        async with app.run_test():
            try:
                for issue in issues:
                    assert await asyncio.to_thread(column.started[issue.number].wait, 5)

                column.release[2].set()

                async def wait_for_second_issue() -> None:
                    while True:
                        content = app.query_one("#task-progress", Static).content
                        progress = content.plain if isinstance(content, Text) else str(content)
                        if progress == "Refreshed org/repo#2 (1/2)":
                            return
                        await asyncio.sleep(0.01)

                await asyncio.wait_for(wait_for_second_issue(), timeout=5)

                assert column.table.row_count == 0

                column.release[1].set()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)

                assert [row.data for row in column.table.selectable_rows] == [["First"], ["Second"]]
            finally:
                for event in column.release.values():
                    event.set()

    asyncio.run(run_test())
