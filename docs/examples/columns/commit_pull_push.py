from __future__ import annotations

import os
from pathlib import Path

from devboard._internal.default_board import ToCommit, ToPull, ToPush
from devboard._internal.projects import Project as BaseProject

BASE_DIR = Path(os.environ["PROJECTS_DIR"])


class Project(BaseProject):
    @classmethod
    def list_projects(cls):
        for filedir in BASE_DIR.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield cls(filedir)


class ToCommit(ToCommit):
    def list_projects(self):
        yield from Project.list_projects()


class ToPull(ToPull):
    def list_projects(self):
        yield from Project.list_projects()


class ToPush(ToPush):
    def list_projects(self):
        yield from Project.list_projects()


columns = [ToCommit, ToPull, ToPush]
