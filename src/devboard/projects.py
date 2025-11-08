"""Git utilities."""

from __future__ import annotations

import contextlib
import re
from collections import defaultdict
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import ClassVar, Iterator

from git import Commit, GitCommandError, Head, Repo, TagReference  # type: ignore[attr-defined]


@dataclass
class Status:
    """Git status data."""

    added: list[Path]
    """Added files."""
    deleted: list[Path]
    """Deleted files."""
    modified: list[Path]
    """Modified files."""
    renamed: list[Path]
    """Renamed files."""
    typechanged: list[Path]
    """Type-changed files."""
    untracked: list[Path]
    """Untracked files."""


@dataclass(eq=True, order=True, frozen=True)
class Project:
    """A class representing development projects.

    It is instantiated with a path, and then provides
    many utility properties and methods.
    """

    LOCKS: ClassVar[dict[Project, Lock]] = defaultdict(Lock)

    DEFAULT_BRANCHES: ClassVar[tuple[str, ...]] = ("main", "master")
    """Name of common default branches. Mainly useful to compute unreleased commits."""
    path: Path
    """Path of the project on the file-system."""

    def __str__(self) -> str:
        return self.name

    @property
    def repo(self) -> Repo:
        """GitPython's `Repo` object."""
        return Repo(self.path)

    @property
    def name(self) -> str:
        """Name of the project."""
        return self.path.name

    @property
    def is_dirty(self) -> bool:
        """Whether the project is in a "dirty" state (uncommitted modifications)."""
        return self.repo.is_dirty(untracked_files=True)

    @property
    def status(self) -> Status:
        """Status of the project."""
        diff = self.repo.index.diff(None)
        return Status(
            added=[Path(added) for added in diff.iter_change_type("A")],
            deleted=[Path(deleted.a_path) for deleted in diff.iter_change_type("D")],
            modified=[Path(modified.a_path) for modified in diff.iter_change_type("M")],
            renamed=[Path(renamed) for renamed in diff.iter_change_type("R")],
            typechanged=[Path(typechanged) for typechanged in diff.iter_change_type("T")],
            untracked=[Path(untracked) for untracked in self.repo.untracked_files],
        )

    @property
    def status_line(self) -> str:
        """Status of the project, as a string."""
        st = self.status
        parts = []
        if added := len(st.added):
            parts.append(f"{added}A")
        if deleted := len(st.deleted):
            parts.append(f"{deleted}D")
        if modified := len(st.modified):
            parts.append(f"{modified}M")
        if renamed := len(st.renamed):
            parts.append(f"{renamed}R")
        if typechanged := len(st.typechanged):
            parts.append(f"{typechanged}T")
        if untracked := len(st.untracked):
            parts.append(f"{untracked}U")
        return " ".join(parts)

    def unpushed(self, remote: str = "origin") -> dict[str, int]:
        """Number of unpushed commits, per branch."""
        result = {}
        for branch in self.repo.branches:  # type: ignore[attr-defined]
            with contextlib.suppress(GitCommandError):
                result[branch.name] = len(list(self.repo.iter_commits(f"{remote}/{branch.name}..{branch.name}")))
        return result

    def unpulled(self, remote: str = "origin") -> dict[str, int]:
        """Number of unpulled commits, per branch."""
        result = {}
        for branch in self.repo.branches:  # type: ignore[attr-defined]
            with contextlib.suppress(GitCommandError):
                result[branch.name] = len(list(self.repo.iter_commits(f"{branch.name}..{remote}/{branch.name}")))
        return result

    @property
    def branch(self) -> Head:
        """Currently checked out branch."""
        return self.repo.active_branch

    @property
    def default_branch(self) -> str:
        """Default branch (or main branch), as checked out when cloning."""
        for branch in self.DEFAULT_BRANCHES:
            if branch in self.repo.references:
                return branch
        try:
            origin = self.repo.git.remote("show", "origin")
        except GitCommandError as error:
            raise ValueError(f"Cannot infer default branch for repo {self.name}") from error
        if match := re.search(r"\s*HEAD branch:\s*(.*)", origin):
            return match.group(1)
        raise ValueError(f"Cannot infer default branch for repo {self.name}")

    @contextmanager
    def checkout(self, branch: str | None) -> Iterator[None]:
        """Checkout branch, restore previous one when exiting."""
        if not branch:
            yield
            return
        current = self.branch
        if branch == current:
            yield
            return
        self.repo.branches[branch].checkout()  # type: ignore[index]
        try:
            yield
        finally:
            current.checkout()

    def pull(self, branch: str | None = None) -> None:
        """Pull branch."""
        with self.checkout(branch):
            self.repo.remotes.origin.pull()

    def push(self, branch: str | None = None) -> None:
        """Push branch."""
        with self.checkout(branch):
            self.repo.remotes.origin.push()

    def delete(self, branch: str) -> None:
        """Delete branch."""
        self.repo.delete_head(branch, force=True)

    def unreleased(self, branch: str | None = None) -> list[Commit]:
        """List unreleased commits."""
        commits = []
        if branch is None:
            try:
                branch = self.default_branch
            except ValueError:
                return []
        iterator = self.repo.iter_commits(branch)
        try:
            latest_tagged_commit = self.latest_tag.commit
        except IndexError:
            return list(iterator)
        for commit in iterator:
            if commit == latest_tagged_commit:
                break
            commits.append(commit)
        return commits

    def fetch(self) -> None:
        """Fetch."""
        with suppress(AttributeError, GitCommandError):
            self.repo.remotes.origin.fetch()
        with suppress(AttributeError, GitCommandError):
            self.repo.remotes.upstream.fetch()

    @property
    def latest_tag(self) -> TagReference:
        """Latest tag."""
        return sorted(self.repo.tags, key=lambda t: t.commit.committed_datetime)[-1]

    def lock(self) -> bool:
        """Lock project."""
        return self.LOCKS[self].acquire(blocking=False)

    def unlock(self) -> None:
        """Unlock project."""
        self.LOCKS[self].release()
