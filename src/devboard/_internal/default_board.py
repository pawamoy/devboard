"""User configuration of columns.

The only object that must be defined in this module is `columns`,
which is a list of `Column` instances.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, ClassVar

from git import TYPE_CHECKING, GitCommandError

from devboard import Column, Row
from devboard import Project as BaseProject

if TYPE_CHECKING:
    from collections.abc import Iterator

BASE_DIR = Path(os.getenv("DEVBOARD_PROJECTS", Path.home() / "dev")).expanduser()
"""The base directory containing all your Git projects.

This variable is only used to list projects in `Project.list_projects`
and has no special meaning for Devboard.
"""


class Project(BaseProject):
    """Customized project class.

    The original `Project` is sub-classed for demonstration purpose.
    Feel free to add any attribute, property or method to it,
    to serve your own needs. You can also override its existing
    property and methods if needed. In the default class below,
    we add the `list_projects` class method that will be passed
    to `Column` instances, allowing them to iterate on your projects.
    """

    @classmethod
    def list_projects(cls) -> Iterator[Project]:
        """List all Git projects in a base directory."""
        for filedir in BASE_DIR.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield cls(filedir)


class ToCommit(Column):
    """A column showing projects with uncommitted changes."""

    TITLE = "To Commit"
    HEADERS = ("Project", "Details")
    THREADED = False
    BINDINGS: ClassVar = [
        ("s", "apply('status')", "Show status"),
        ("d", "apply('diff')", "Show diff"),
    ]

    def list_projects(self) -> Iterator[Project]:
        """List projects for this column."""
        yield from Project.list_projects()

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Any, ...]]:  # type: ignore[override]
        """Scan a project, feeding rows to the table.

        It returns a single row with the project and its status line.
        """
        return [(project, project.status_line)] if project.is_dirty else []

    def apply(self, action: str, row: Row) -> None:
        """Process actions.

        It handles two actions: `status` and `diff`.

        - `status`: Show the Git status of the selected project in a modal window
        - `diff`: Show the Git diff of the selected project in a modal window.
        """
        if action == "status":
            self.modal(text=row.project.repo.git(c="color.status=always").status())
        if action == "diff":
            self.modal(text=row.project.repo.git(c="color.ui=always").diff())
        raise ValueError(f"Unknown action '{action}'")


class ToPull(Column):
    """A column showing branches with commits that should be pulled."""

    TITLE = "To Pull"
    HEADERS = ("Project", "Branch", "Commits")
    BINDINGS: ClassVar = [
        ("p", "apply('pull')", "Pull"),
        ("d", "apply('delete')", "Delete branch"),
    ]

    def list_projects(self) -> Iterator[Project]:
        """List projects for this column."""
        yield from Project.list_projects()

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Any, ...]]:  # type: ignore[override]
        """Scan a project, feeding rows to the table.

        It returns multiple rows, one for each branch having commits to pull from the remote.
        """
        return [(project, branch, commits) for branch, commits in project.unpulled().items() if commits]

    def apply(self, action: str, row: Row) -> None:  # noqa: ARG002
        """Process actions.

        It handles a single default action: running `git pull` for the selected row
        (project and branch).
        """
        project, branch, _ = row.data
        message = f"Pulling branch [i]{branch}[/] in [i]{project}[/]"
        if not project.lock():
            self.notify_warning(f"Prevented: {message}: An operation is ongoing")
            return
        if not project.is_dirty:
            self.notify_info(f"Started: {message}")
            try:
                project.pull(branch)
            except GitCommandError as error:
                self.notify_error(f"{message}: {error}", timeout=10)
            else:
                self.notify_success(f"Finished: {message}")
                row.remove()
        else:
            self.notify_warning(f"Prevented: {message}: project is dirty")
        project.unlock()


class ToPush(Column):
    """A column showing branches with commits that should be pushed."""

    TITLE = "To Push"
    HEADERS = ("Project", "Branch", "Commits")
    BINDINGS: ClassVar = [
        ("p", "apply('push')", "Push"),
    ]

    def list_projects(self) -> Iterator[Project]:
        """List projects for this column."""
        yield from Project.list_projects()

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Any, ...]]:  # type: ignore[override]
        """Scan a project, feeding rows to the table.

        It returns multiple rows, one for each branch having commits to push to the remote.
        """
        return [(project, branch, commits) for branch, commits in project.unpushed().items() if commits]

    def apply(self, action: str, row: Row) -> None:  # noqa: ARG002
        """Process actions.

        It handles a single default action: running `git push` for the selected row
        (project and branch).
        """
        project, branch, _ = row.data
        message = f"Pushing branch [i]{branch}[/] in [i]{project}[/]"
        if not project.lock():
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
        project.unlock()


class ToRelease(Column):
    """A column showing projects with commits that should be released."""

    TITLE = "To Release"
    HEADERS = ("Project", "Details")

    def list_projects(self) -> Iterator[Project]:
        """List projects for this column."""
        yield from Project.list_projects()

    @staticmethod
    def populate_rows(project: Project) -> list[tuple[Any, ...]]:  # type: ignore[override]
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


columns = [
    ToCommit,
    ToPull,
    ToPush,
    ToRelease,
]
