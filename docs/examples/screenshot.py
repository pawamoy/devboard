import asyncio
import hashlib
import inspect
import os
from collections.abc import Hashable
from pathlib import Path
from tempfile import gettempdir

from textual.pilot import Pilot

from devboard import Devboard

TMP_DIR = Path(gettempdir(), "devboard")
SCREENSHOT_CACHE = TMP_DIR / "screenshots"
REPOSITORIES_DIR = TMP_DIR / "repositories"
PROJECTS_DIR = TMP_DIR / "projects"
SCREENSHOT_SOURCE = Path("docs/examples/screenshot.py")


def _get_cache_key(path: Path, *args: Hashable, **kwargs: Hashable) -> str:
    hash = hashlib.md5()  # noqa: S324
    package_dir = Path(inspect.getfile(Devboard)).parent
    sources = [path, SCREENSHOT_SOURCE, *sorted(package_dir.glob("*.py")), *sorted(package_dir.glob("*.tcss"))]
    for source in sources:
        hash.update(source.read_bytes())
    hash.update(f"{args}-{kwargs}".encode("utf-8"))
    return f"{hash.hexdigest()}.svg"


def screenshot(
    board: str,
    size: tuple[int, int] = (80, 24),
    press: tuple[str, ...] = (),
    env: tuple[tuple[str, str], ...] = (),
) -> str:
    """Render a documentation example as an SVG screenshot."""
    path = Path("docs/examples", board).with_suffix(".py")
    SCREENSHOT_CACHE.mkdir(parents=True, exist_ok=True)

    screenshot_path = SCREENSHOT_CACHE / _get_cache_key(path, size, press, env)
    if screenshot_path.exists():
        return screenshot_path.read_text(encoding="utf-8")

    environment = {"PROJECTS_DIR": str(PROJECTS_DIR), **dict(env)}
    previous_environment = {name: os.environ.get(name) for name in environment}
    os.environ.update(environment)
    try:
        app = Devboard(board=path, background_tasks=False)
        svg = _take_svg_screenshot(app, size=size, press=press)
        screenshot_path.write_text(svg, encoding="utf-8")
        return svg
    finally:
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _take_svg_screenshot(app: Devboard, *, size: tuple[int, int], press: tuple[str, ...]) -> str:
    """Run an app headlessly and export its final screen."""

    async def capture(pilot: Pilot) -> None:
        await pilot.pause()
        await asyncio.wait_for(pilot.app.workers.wait_for_complete(), timeout=30)
        if press:
            await pilot.press(*press)
        await pilot.wait_for_scheduled_animations()
        await pilot.pause()
        pilot.app.exit(pilot.app.export_screenshot())

    svg = app.run(headless=True, size=size, auto_pilot=capture)
    if not isinstance(svg, str):
        raise TypeError("The screenshot run ended without SVG output")
    return svg
