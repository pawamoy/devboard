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

"""Deterministic application used by visual regression tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from devboard import Board, Column, Devboard, Project

if TYPE_CHECKING:
    from collections.abc import Iterator


class ChangesColumn(Column[Project]):
    """Projects with local changes."""

    TITLE = "Local Changes"
    HEADERS = ("Project", "Status")

    def list_items(self) -> Iterator[Project]:
        """Return projects shown in this test column."""
        yield Project(Path("/workspaces/atlas"))
        yield Project(Path("/workspaces/devboard"))

    def populate_rows(self, project: Project) -> list[tuple[Project, str]]:
        """Return deterministic local-change data."""
        statuses = {"atlas": "2M 1U", "devboard": "1A"}
        return [(project, statuses[project.name])]


class UpdatesColumn(Column[Project]):
    """Branches with remote updates."""

    TITLE = "Remote Updates"
    HEADERS = ("Project", "Branch", "Behind")

    def list_items(self) -> Iterator[Project]:
        """Return projects shown in this test column."""
        yield Project(Path("/workspaces/atlas"))
        yield Project(Path("/workspaces/toolkit"))

    def populate_rows(self, project: Project) -> list[tuple[Project, str, int]]:
        """Return deterministic remote-update data."""
        branches = {"atlas": ("main", 3), "toolkit": ("docs", 1)}
        branch, count = branches[project.name]
        return [(project, branch, count)]


class SnapshotDevboard(Devboard):
    """A board that does not read user configuration or Git repositories."""

    def __init__(self) -> None:
        """Initialize a deterministic board."""
        super().__init__(board="snapshot", background_tasks=False, workers=1)

    def _load_board(self) -> Board:
        """Return the deterministic board used by snapshots."""
        self._board_key = "snapshot"
        return Board(
            [ChangesColumn(), UpdatesColumn()],
            bindings=[
                ("ctrl+r", "refresh", "Refresh"),
                ("ctrl+shift+r", "force_refresh", "Force refresh"),
            ],
        )
