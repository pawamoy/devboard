from __future__ import annotations

import os
from pathlib import Path

from devboard._internal.default_board import ProjectsBoard, ToCommit, ToPull, ToPush, ToRelease
from devboard._internal.projects import Project as BaseProject

BASE_DIR = Path(os.environ["PROJECTS_DIR"])


class Project(BaseProject):
    @classmethod
    def list_items(cls):
        for filedir in BASE_DIR.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield cls(filedir)


class ToCommit(ToCommit):
    def list_items(self):
        yield from Project.list_items()


class ToPull(ToPull):
    def list_items(self):
        yield from Project.list_items()


class ToPush(ToPush):
    def list_items(self):
        yield from Project.list_items()


class ToRelease(ToRelease):
    def list_items(self):
        yield from Project.list_items()


board = ProjectsBoard(
    [ToCommit, ToPull, ToPush, ToRelease],
    bindings=[
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+shift+r", "force_refresh", "Force refresh"),
    ],
    force_refresh_on_startup=True,
)
