from __future__ import annotations

import os
import time
from pathlib import Path

from devboard._internal.default_board import ToCommit, ToPull, ToPush, ToRelease
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

    def apply(self, action, row):
        project, branch, _ = row.data
        message = f"Pulling branch [i]{branch}[/] in [i]{project}[/]"
        if not project.is_dirty:
            msg_type = os.environ["msgtype"]
            if msg_type == "error":
                error = (
                    "fatal: unable to access 'https://github.com/pawamoy/git-changelog': "
                    "Failed to connect to (domain) port 443: Timed Out"
                )
                self.notify_error(f"{message}: {error}")
            elif msg_type == "started":
                self.notify_info(f"Started: {message}")
            elif msg_type == "finished":
                self.notify_success(f"Finished: {message}")
                row.remove()
            elif msg_type == "ongoing":
                self.notify_info(f"Started: {message}")
                self.notify_warning(f"Prevented: {message}: An operation is ongoing")
        else:
            self.notify_warning(f"Prevented: {message}: project is dirty")


class ToPush(ToPush):
    def list_projects(self):
        yield from Project.list_projects()


class ToRelease(ToRelease):
    def list_projects(self):
        yield from Project.list_projects()


columns = [ToCommit, ToPull, ToPush, ToRelease]
