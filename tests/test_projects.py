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

"""Tests for project coordination."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from devboard import Project

if TYPE_CHECKING:
    from pathlib import Path


def test_lock_is_shared_by_resolved_path(tmp_path: Path) -> None:
    """Separate objects and path aliases coordinate access to one repository."""
    repository = tmp_path / "repository"
    alias = tmp_path / "alias"
    repository.mkdir()
    alias.symlink_to(repository, target_is_directory=True)
    owner = Project(repository)
    contender = Project(alias)

    assert owner.lock()
    try:
        assert not contender.lock()
    finally:
        owner.unlock()

    assert contender.lock()
    contender.unlock()


def test_locked_context_releases_after_error(tmp_path: Path) -> None:
    """An exception cannot leave a project path locked."""
    project = Project(tmp_path)

    def fail_while_locked() -> None:
        with project.locked() as acquired:
            assert acquired
            raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        fail_while_locked()

    assert project.lock()
    project.unlock()


def test_fetch_locked_skips_a_busy_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fetch only when the project path lock is available."""
    project = Project(tmp_path)
    fetched: list[Path] = []
    monkeypatch.setattr(Project, "fetch", lambda self: fetched.append(self.path))

    assert project.fetch_locked()
    assert fetched == [tmp_path]

    assert project.lock()
    try:
        assert not project.fetch_locked()
    finally:
        project.unlock()

    assert fetched == [tmp_path]
