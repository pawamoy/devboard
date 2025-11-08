"""Devboard package.

A development dashboard for your projects.
"""

from __future__ import annotations

from devboard._internal.app import Devboard
from devboard._internal.board import Column, DataTable, Row
from devboard._internal.cli import get_parser, main
from devboard._internal.datatable import Checkbox, SelectableRow, SelectableRowsDataTable
from devboard._internal.modal import Modal, ModalMixin
from devboard._internal.notifications import NotifyMixin
from devboard._internal.projects import Project, Status

__all__: list[str] = [
    "Checkbox",
    "Column",
    "DataTable",
    "Devboard",
    "Modal",
    "ModalMixin",
    "NotifyMixin",
    "Project",
    "Row",
    "SelectableRow",
    "SelectableRowsDataTable",
    "Status",
    "get_parser",
    "main",
]
