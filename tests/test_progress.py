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
from functools import partial
from threading import Event
from typing import TYPE_CHECKING, cast

import pytest
from rich.text import Text
from textual.widgets import Footer, Static

from devboard import Column, Devboard, Project
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


class ProgressColumn(Column[Project]):
    HEADERS = ("Project",)

    def __init__(self, projects: list[ProgressProject]) -> None:
        """Initialize the column with controlled projects."""
        super().__init__()
        self.projects = projects

    def list_projects(self) -> Iterator[ProgressProject]:
        """Return the test projects."""
        yield from self.projects

    def populate_rows(self, project: Project) -> list[tuple[Project]]:
        """Wait until the test allows this project's scan to complete."""
        progress_project = cast("ProgressProject", project)
        progress_project.scan_started.set()
        assert progress_project.release_scan.wait(5)
        return [(project,)]


@pytest.fixture(name="projects")
def _fixture_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[list[ProgressProject]]:
    projects = [ProgressProject(tmp_path / name) for name in ("first[repo]", "second", "third")]
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(app_module, "_DEBUG", False)
    monkeypatch.setattr(Devboard, "_load_columns", lambda self: [ProgressColumn(projects)])
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


def test_startup_shows_latest_completion_and_clears_when_finished(projects: list[ProgressProject]) -> None:
    """Count completed tasks in each phase, including out-of-order fetches."""

    async def run_test() -> None:
        app = Devboard(board="test-board", workers=3)
        async with app.run_test(size=(100, 20)) as pilot:
            try:
                for project in projects:
                    assert await asyncio.to_thread(project.scan_started.wait, 5)
                await _wait_for_progress(app, "")
                await pilot.pause()
                status = app.query_one("#task-progress", Static)
                footer = app.query_one(Footer)
                assert status.region.y == 18
                assert status.region.height == 1
                assert footer.region.y == 19
                assert app.query_one(Column).region.bottom <= status.region.y

                projects[0].release_scan.set()
                await _wait_for_progress(app, f"Scanned {projects[0]} (1/3)")
                projects[1].release_scan.set()
                await _wait_for_progress(app, f"Scanned {projects[1]} (2/3)")
                projects[2].release_scan.set()
                for project in projects:
                    assert await asyncio.to_thread(project.fetch_started.wait, 5)

                projects[1].release_fetch.set()
                await _wait_for_progress(app, f"Fetched {projects[1]} (1/3)")
                projects[0].release_fetch.set()
                await _wait_for_progress(app, f"Fetched {projects[0]} (2/3)")
                projects[2].release_fetch.set()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
                await _wait_for_progress(app, "")
            finally:
                for project in projects:
                    project.release_scan.set()
                    project.release_fetch.set()

    asyncio.run(run_test())


def test_fetch_progress_waits_for_completion(projects: list[ProgressProject]) -> None:
    """Running and queued repositories do not replace the last completed fetch."""
    for project in projects:
        project.release_scan.set()

    async def run_test() -> None:
        app = Devboard(board="test-board", workers=1, background_tasks=False)
        async with app.run_test():
            try:
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
                await _wait_for_progress(app, "")
                app.run_worker(partial(app._fetch_projects, iter(projects)), thread=True)
                assert await asyncio.to_thread(projects[0].fetch_started.wait, 5)
                await _wait_for_progress(app, "")
                assert not projects[1].fetch_started.is_set()

                projects[0].release_fetch.set()
                assert await asyncio.to_thread(projects[1].fetch_started.wait, 5)
                await _wait_for_progress(app, f"Fetched {projects[0]} (1/3)")
                projects[1].release_fetch.set()
                assert await asyncio.to_thread(projects[2].fetch_started.wait, 5)
                await _wait_for_progress(app, f"Fetched {projects[1]} (2/3)")
                projects[2].release_fetch.set()
                await asyncio.wait_for(app.workers.wait_for_complete(), timeout=5)
                await _wait_for_progress(app, "")
            finally:
                for project in projects:
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
                await _wait_for_progress(app, f"Fetched {projects[0]} (1/3)")
                app.workers.cancel_all()
                await _wait_for_progress(app, "")
            finally:
                for project in projects:
                    project.release_fetch.set()

    asyncio.run(run_test())
