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

"""Tests for displaying the most recently completed repository task."""

from __future__ import annotations

import asyncio
from threading import Event
from typing import TYPE_CHECKING, cast

import pytest
from rich.text import Text
from textual.widgets import Footer, Static

from devboard import Board, Column, Devboard, Project
from devboard._internal import app as app_module
from devboard._internal import cache

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class ProgressProject(Project):
    def __init__(self, path: Path) -> None:
        """Initialize a project whose tasks wait for the test to release them."""
        super().__init__(path)
        self.release_scan = Event()
        self.release_fetch = Event()
        self.scan_started = Event()
        self.fetch_started = Event()

    def fetch(self) -> None:
        """Wait without running Git or accessing the network."""
        self.fetch_started.set()
        assert self.release_fetch.wait(5)


class FetchingBoard(Board):
    """Fetch projects during forced refreshes."""

    def force_refresh_item(self, item: object, /) -> None:
        """Fetch project data before scanning it."""
        if isinstance(item, Project):
            item.fetch_locked()


class ProgressColumn(Column[Project]):
    HEADERS = ("Project",)

    def __init__(self, projects: list[ProgressProject]) -> None:
        """Initialize the column with controlled projects."""
        super().__init__()
        self.projects = projects

    def list_items(self) -> Iterator[ProgressProject]:
        """Return the test projects."""
        yield from self.projects

    def populate_rows(self, project: Project) -> list[tuple[Project]]:
        """Wait until the test allows this project's scan to complete."""
        progress_project = cast("ProgressProject", project)
        progress_project.scan_started.set()
        assert progress_project.release_scan.wait(5)
        return [(project,)]


class ReportingColumn(Column[object]):
    """A column that reports progress while listing its items."""

    def __init__(self) -> None:
        """Initialize the events that control item listing."""
        super().__init__()
        self.clear_progress = Event()
        self.progress_cleared = Event()
        self.release = Event()
        self.started = Event()

    def list_items(self) -> Iterator[object]:
        """Report progress until the test clears and releases the scan."""
        self.report_progress("Fetching remote backlog")
        self.started.set()
        assert self.clear_progress.wait(5)
        self.report_progress()
        self.progress_cleared.set()
        assert self.release.wait(5)
        yield from ()


@pytest.fixture(name="projects")
def _fixture_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[list[ProgressProject]]:
    projects = [ProgressProject(tmp_path / name) for name in ("first[repo]", "second", "third")]
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(app_module, "_DEBUG", False)
    board = FetchingBoard([ProgressColumn(projects)], force_refresh_on_startup=True)
    monkeypatch.setattr(Devboard, "_load_board", lambda self: board)
    try:
        yield projects
    finally:
        for project in projects:
            project.release_scan.set()
            project.release_fetch.set()


async def _wait_for_progress(app: Devboard, expected: str) -> None:
    async def wait() -> None:
        while True:
            content = app.query_one("#task-progress", Static).content
            text = content.plain if isinstance(content, Text) else str(content)
            if text == expected:
                return
            await asyncio.sleep(0.01)

    await asyncio.wait_for(wait(), timeout=5)


def test_startup_force_refreshes_each_project_before_scanning(projects: list[ProgressProject]) -> None:
    """Scan each project as soon as its fetch finishes."""

    async def run_test() -> None:
        app = Devboard(board="test-board", workers=3)
        async with app.run_test(size=(100, 20)) as pilot:
            try:
                for project in projects:
                    assert await asyncio.to_thread(project.fetch_started.wait, 5)
                await _wait_for_progress(app, "")
                await pilot.pause()
                status = app.query_one("#task-progress", Static)
                footer = app.query_one(Footer)
                assert status.region.y == 18
                assert status.region.height == 1
                assert footer.region.y == 19
                assert app.query_one(Column).region.bottom <= status.region.y

                # The first project starts scanning while the other fetches remain blocked.
                projects[0].release_fetch.set()
                assert await asyncio.to_thread(projects[0].scan_started.wait, 5)
                assert not projects[1].scan_started.is_set()
                assert not projects[2].scan_started.is_set()

                projects[0].release_scan.set()
                await _wait_for_progress(app, f"Force-refreshed {projects[0]} (1/3)")

                projects[1].release_fetch.set()
                assert await asyncio.to_thread(projects[1].scan_started.wait, 5)
                projects[1].release_scan.set()
                await _wait_for_progress(app, f"Force-refreshed {projects[1]} (2/3)")

                projects[2].release_fetch.set()
                assert await asyncio.to_thread(projects[2].scan_started.wait, 5)
                projects[2].release_scan.set()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
                await _wait_for_progress(app, "")
            finally:
                for project in projects:
                    project.release_scan.set()
                    project.release_fetch.set()

    asyncio.run(run_test())


def test_force_refresh_progress_waits_for_fetch_and_scan(projects: list[ProgressProject]) -> None:
    """Report a project only after both its fetch and scan finish."""
    for project in projects:
        project.release_scan.set()

    async def run_test() -> None:
        app = Devboard(board="test-board", workers=1, background_tasks=False)
        async with app.run_test():
            try:
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
                await _wait_for_progress(app, "")
                for project in projects:
                    project.release_scan.clear()
                    project.scan_started.clear()

                app.force_refresh_board()
                assert await asyncio.to_thread(projects[0].fetch_started.wait, 5)
                await _wait_for_progress(app, "")
                assert not projects[1].fetch_started.is_set()

                projects[0].release_fetch.set()
                assert await asyncio.to_thread(projects[0].scan_started.wait, 5)
                await _wait_for_progress(app, "")
                projects[0].release_scan.set()
                assert await asyncio.to_thread(projects[1].fetch_started.wait, 5)
                await _wait_for_progress(app, f"Force-refreshed {projects[0]} (1/3)")

                projects[1].release_fetch.set()
                assert await asyncio.to_thread(projects[1].scan_started.wait, 5)
                projects[1].release_scan.set()
                assert await asyncio.to_thread(projects[2].fetch_started.wait, 5)
                await _wait_for_progress(app, f"Force-refreshed {projects[1]} (2/3)")

                projects[2].release_fetch.set()
                assert await asyncio.to_thread(projects[2].scan_started.wait, 5)
                projects[2].release_scan.set()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
                await _wait_for_progress(app, "")
            finally:
                for project in projects:
                    project.release_scan.set()
                    project.release_fetch.set()

    asyncio.run(run_test())


def test_cancelled_tasks_clear_progress(projects: list[ProgressProject]) -> None:
    """Cancellation clears the status while repository threads finish stopping."""
    for project in projects:
        project.release_scan.set()

    async def run_test() -> None:
        app = Devboard(board="test-board", workers=3)
        async with app.run_test():
            try:
                for project in projects:
                    assert await asyncio.to_thread(project.fetch_started.wait, 5)
                projects[0].release_fetch.set()
                projects[0].release_scan.set()
                await _wait_for_progress(app, f"Force-refreshed {projects[0]} (1/3)")
                app.workers.cancel_all()
                await _wait_for_progress(app, "")
            finally:
                for project in projects:
                    project.release_fetch.set()

    asyncio.run(run_test())


def test_column_can_report_and_clear_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    """A column can update and clear the status bar from the scan worker."""
    column = ReportingColumn()
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False)
        async with app.run_test():
            try:
                assert await asyncio.to_thread(column.started.wait, 5)
                await _wait_for_progress(app, "Fetching remote backlog")

                column.clear_progress.set()
                assert await asyncio.to_thread(column.progress_cleared.wait, 5)
                await _wait_for_progress(app, "")

                column.release.set()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
            finally:
                column.clear_progress.set()
                column.release.set()

    asyncio.run(run_test())


def test_cancelled_worker_clears_column_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancelling a worker clears progress that its column reported."""
    column = ReportingColumn()
    monkeypatch.setattr(Devboard, "_load_board", lambda self: Board([column]))

    async def run_test() -> None:
        app = Devboard(board="test-board", background_tasks=False)
        async with app.run_test():
            try:
                assert await asyncio.to_thread(column.started.wait, 5)
                await _wait_for_progress(app, "Fetching remote backlog")

                app.workers.cancel_all()

                await _wait_for_progress(app, "")
            finally:
                column.clear_progress.set()
                column.release.set()

    asyncio.run(run_test())
