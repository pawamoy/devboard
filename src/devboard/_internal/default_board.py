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

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from git import GitCommandError

from devboard import Board, Column, Project, Row, row_action

if TYPE_CHECKING:
    from collections.abc import Iterator

BASE_DIR = Path(os.getenv("DEVBOARD_PROJECTS", Path.home() / "dev")).expanduser()
"""The base directory containing all your Git projects.

This variable is only used to list projects in `MyProject.list_items`
and has no special meaning for Devboard.
"""


class MyProject(Project):
    """Customized project class.

    The original `Project` is sub-classed for demonstration purpose.
    Feel free to add any attribute, property or method to it,
    to serve your own needs. You can also override its existing
    property and methods if needed. In the default class below,
    we add the `list_items` class method that will be passed
    to `Column` instances, allowing them to iterate on your projects.
    """

    @classmethod
    def list_items(cls) -> Iterator[MyProject]:
        """List all Git projects in a base directory."""
        for filedir in BASE_DIR.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield cls(filedir)


class ToCommit(Column[MyProject]):
    """A column showing projects with uncommitted changes."""

    TITLE = "To Commit"
    HEADERS = ("Project", "Details")
    THREADED = False
    BINDINGS: ClassVar = [
        ("s", "status", "Show status"),
        ("d", "diff", "Show diff"),
    ]

    def list_items(self) -> Iterator[MyProject]:
        """List projects for this column."""
        yield from MyProject.list_items()

    def populate_rows(self, project: MyProject) -> list[tuple[Any, ...]]:
        """Scan a project, feeding rows to the table.

        It returns a single row with the project and its status line.
        """
        status_line = project.status_line
        return [(project, status_line)] if status_line else []

    @row_action
    def action_status(self, row: Row[MyProject]) -> None:
        """Show the selected project's Git status."""
        self.modal(text=row.item.repo.git(c="color.status=always").status())

    @row_action
    def action_diff(self, row: Row[MyProject]) -> None:
        """Show the selected project's Git diff."""
        self.modal(text=row.item.repo.git(c="color.ui=always").diff())


class ToPull(Column[MyProject]):
    """A column showing branches with commits that should be pulled."""

    TITLE = "To Pull"
    HEADERS = ("Project", "Branch", "Commits")
    BINDINGS: ClassVar = [
        ("p", "pull", "Pull"),
        ("d", "delete", "Delete branch"),
    ]

    def list_items(self) -> Iterator[MyProject]:
        """List projects for this column."""
        yield from MyProject.list_items()

    def populate_rows(self, project: MyProject) -> list[tuple[Any, ...]]:
        """Scan a project, feeding rows to the table.

        It returns multiple rows, one for each branch having commits to pull from the remote.
        """
        return [(project, branch, commits) for branch, commits in project.unpulled().items() if commits]

    @row_action
    def action_pull(self, row: Row[MyProject]) -> None:
        """Pull the branch in a selected row."""
        self._update_branch(row, delete=False)

    @row_action
    def action_delete(self, row: Row[MyProject]) -> None:
        """Delete the branch in a selected row."""
        self._update_branch(row, delete=True)

    def _update_branch(self, row: Row[MyProject], *, delete: bool) -> None:
        """Pull or delete the branch in a selected row."""
        project, branch, _ = row.data
        if delete:
            message = f"Deleting branch [i]{branch}[/] in [i]{project}[/]"
        else:
            message = f"Pulling branch [i]{branch}[/] in [i]{project}[/]"

        with project.locked() as acquired:
            if not acquired:
                self.notify_warning(f"Prevented: {message}: An operation is ongoing")
                return
            if not delete and project.is_dirty:
                self.notify_warning(f"Prevented: {message}: project is dirty")
                return

            self.notify_info(f"Started: {message}")
            try:
                if delete:
                    project.delete(branch)
                else:
                    project.pull(branch)
            except GitCommandError as error:
                self.notify_error(f"{message}: {error}", timeout=10)
            else:
                self.notify_success(f"Finished: {message}")
                row.remove()


class ToPush(Column[MyProject]):
    """A column showing branches with commits that should be pushed."""

    TITLE = "To Push"
    HEADERS = ("Project", "Branch", "Commits")
    BINDINGS: ClassVar = [
        ("p", "push", "Push"),
    ]

    def list_items(self) -> Iterator[MyProject]:
        """List projects for this column."""
        yield from MyProject.list_items()

    def populate_rows(self, project: MyProject) -> list[tuple[Any, ...]]:
        """Scan a project, feeding rows to the table.

        It returns multiple rows, one for each branch having commits to push to the remote.
        """
        return [(project, branch, commits) for branch, commits in project.unpushed().items() if commits]

    @row_action
    def action_push(self, row: Row[MyProject]) -> None:
        """Push the branch in a selected row."""
        project, branch, _ = row.data
        message = f"Pushing branch [i]{branch}[/] in [i]{project}[/]"
        with project.locked() as acquired:
            if not acquired:
                self.notify_warning(f"Prevented: {message}: An operation is ongoing")
                return
            self.notify_info(f"Started: {message}")
            try:
                project.push(branch)
            except GitCommandError as error:
                self.notify_error(f"{message}: {error}", timeout=10)
            else:
                self.notify_success(f"Finished: {message}")
                row.remove()


class ToRelease(Column[MyProject]):
    """A column showing projects with commits that should be released."""

    TITLE = "To Release"
    HEADERS = ("Project", "Details")

    def list_items(self) -> Iterator[MyProject]:
        """List projects for this column."""
        yield from MyProject.list_items()

    def populate_rows(self, project: MyProject) -> list[tuple[Any, ...]]:
        """Scan a project, feeding rows to the table.

        It returns a single row with the project and a summary of commit types.
        """
        commit_types = {"feat": "F", "fix": "X", "refactor": "R", "build": "B", "deps": "D"}
        by_type = dict.fromkeys(commit_types, 0)
        for commit in project.unreleased():
            for commit_type in commit_types:
                summary = (
                    commit.summary
                    if isinstance(commit.summary, str)
                    else bytes(commit.summary).decode("utf-8", errors="ignore")
                )
                if summary.startswith(f"{commit_type}:"):
                    by_type[commit_type] += 1
        parts = [f"{by_type[ct]}{commit_types[ct]}" for ct in commit_types if by_type[ct]]
        if parts:
            return [(project, " ".join(parts))]
        return []


class ProjectsBoard(Board):
    """A board that can fetch Git projects before scanning them."""

    def force_refresh_item(self, item: Any, /) -> None:
        """Fetch a project before its columns scan it."""
        if isinstance(item, Project):
            item.fetch_locked()


board = ProjectsBoard(
    [ToCommit, ToPull, ToPush, ToRelease],
    bindings=[
        ("question_mark", "show_help", "Help"),
        ("ctrl+q, q, escape", "exit", "Exit"),
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+shift+r", "force_refresh", "Force refresh"),
    ],
    force_refresh_on_startup=True,
)
