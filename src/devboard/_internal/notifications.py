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

from textual.app import App


class NotifyMixin:
    """Mixin class to add notify methods."""

    app: App
    """Textual application."""

    def notify_info(self, message: str, timeout: float = 3.0) -> None:
        """Notify information."""
        self.app.notify(f"[b blue]INFO[/]  {message}", severity="information", timeout=timeout)

    def notify_success(self, message: str, timeout: float = 3.0) -> None:
        """Notify success."""
        self.app.notify(f"[b green]SUCCESS[/]  {message}", severity="information", timeout=timeout)

    def notify_warning(self, message: str, timeout: float = 3.0) -> None:
        """Notify warning."""
        self.app.notify(f"[b yellow]WARNING[/]  {message}", severity="warning", timeout=timeout)

    def notify_error(self, message: str, timeout: float = 3.0) -> None:
        """Notify error."""
        self.app.notify(f"[b red]ERROR[/]  {message}", severity="error", timeout=timeout)
