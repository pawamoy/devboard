from __future__ import annotations

import os
from pathlib import Path

from devboard import Board
from devboard._internal.default_board import ToRelease
from devboard._internal.projects import Project as BaseProject

BASE_DIR = Path(os.environ["PROJECTS_DIR"])


class Project(BaseProject):
    @classmethod
    def list_items(cls):
        for filedir in BASE_DIR.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield cls(filedir)


class ToRelease(ToRelease):
    def list_items(self):
        yield from Project.list_items()


board = Board([ToRelease])
