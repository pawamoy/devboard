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
