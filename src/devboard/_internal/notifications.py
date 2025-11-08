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
