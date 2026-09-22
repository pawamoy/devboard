from __future__ import annotations

import os
import time
from pathlib import Path

from devboard import row_action
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

    @row_action
    def action_pull(self, row):
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
