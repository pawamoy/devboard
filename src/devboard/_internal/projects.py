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

import re
from collections import defaultdict
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, ClassVar

from git import Commit, GitCommandError, Head, Repo, TagReference

if TYPE_CHECKING:
    from collections.abc import Iterator


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
    """Locks for projects, to avoid concurrent operations."""
    DEFAULT_BRANCHES: ClassVar[tuple[str, ...]] = ("main", "master")
    """Name of common default branches. Mainly useful to compute unreleased commits."""
    path: Path
    """Path of the project on the file-system."""

    def __str__(self) -> str:
        return self.name

    @cached_property
    def repo(self) -> Repo:
        """GitPython's `Repo` object (cached per instance)."""
        return Repo(self.path)

    @property
    def name(self) -> str:
        """Name of the project."""
        return self.path.name

    @property
    def is_dirty(self) -> bool:
        """Whether the project is in a "dirty" state (uncommitted modifications)."""
        return bool(self.repo.git.status(porcelain=True))

    @property
    def status(self) -> Status:
        """Status of the project.

        Computed from a single `git status --porcelain` call,
        which is much cheaper than diffing index and work tree separately.
        Each file is counted once, in the first matching category:
        untracked, renamed, added, deleted, type-changed, modified.
        """
        status = Status(added=[], deleted=[], modified=[], renamed=[], typechanged=[], untracked=[])
        entries = iter(self.repo.git.status(porcelain=True, z=True).split("\x00"))
        for entry in entries:
            if not entry:
                continue
            state, path = entry[:2], Path(entry[3:])
            if state == "??":
                status.untracked.append(path)
            elif "R" in state:
                status.renamed.append(path)
                next(entries, None)  # Discard the pre-rename path.
            elif "A" in state:
                status.added.append(path)
            elif "D" in state:
                status.deleted.append(path)
            elif "T" in state:
                status.typechanged.append(path)
            else:
                status.modified.append(path)
        return status

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

    @cached_property
    def _tracking(self) -> dict[str, tuple[int, int]]:
        """Ahead/behind counts per branch, relative to its upstream.

        Computed with a single `git for-each-ref` call instead of
        one `git rev-list` subprocess per branch.
        """
        output = self.repo.git.for_each_ref("refs/heads", format="%(refname:short)%00%(upstream:track,nobracket)")
        result = {}
        for line in output.splitlines():
            branch, _, track = line.partition("\x00")
            ahead = behind = 0
            if track and track != "gone":
                for part in track.split(", "):
                    kind, _, count = part.partition(" ")
                    if kind == "ahead":
                        ahead = int(count)
                    elif kind == "behind":
                        behind = int(count)
            result[branch] = (ahead, behind)
        return result

    def unpushed(self) -> dict[str, int]:
        """Number of unpushed commits (compared to the branch upstream), per branch."""
        return {branch: ahead for branch, (ahead, _) in self._tracking.items()}

    def unpulled(self) -> dict[str, int]:
        """Number of unpulled commits (compared to the branch upstream), per branch."""
        return {branch: behind for branch, (_, behind) in self._tracking.items()}

    @property
    def branch(self) -> Head:
        """Currently checked out branch."""
        return self.repo.active_branch

    @property
    def default_branch(self) -> str:
        """Default branch (or main branch), as checked out when cloning."""
        for branch in self.DEFAULT_BRANCHES:
            if branch in self.repo.heads:
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
        self.repo.branches[branch].checkout()
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
        """List unreleased commits (commits since the latest tag reachable from the branch)."""
        if branch is None:
            try:
                branch = self.default_branch
            except ValueError:
                return []
        try:
            latest_tag = self.repo.git.describe(branch, tags=True, abbrev=0)
        except GitCommandError:
            rev = branch  # No tag reachable: everything is unreleased.
        else:
            rev = f"{latest_tag}..{branch}"
        try:
            return list(self.repo.iter_commits(rev))
        except GitCommandError:
            return []

    def fetch(self) -> None:
        """Fetch."""
        with suppress(AttributeError, GitCommandError):
            self.repo.remotes.origin.fetch()
        with suppress(AttributeError, GitCommandError):
            self.repo.remotes.upstream.fetch()

    @property
    def latest_tag(self) -> TagReference:
        """Latest tag (by creation date).

        Raises:
            IndexError: When the repository has no tags.
        """
        name = self.repo.git.for_each_ref("refs/tags", sort="-creatordate", count=1, format="%(refname:short)")
        if not name:
            raise IndexError(f"No tags in repository {self.name}")
        return TagReference(self.repo, f"refs/tags/{name}")

    def lock(self) -> bool:
        """Lock project."""
        return self.LOCKS[self].acquire(blocking=False)

    def unlock(self) -> None:
        """Unlock project."""
        self.LOCKS[self].release()
