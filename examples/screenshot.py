import hashlib
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Hashable

from failprint import Capture
from textual._doc import take_svg_screenshot

from devboard import Devboard

TMP_DIR = Path(gettempdir(), "devboard")
SCREENSHOT_CACHE = TMP_DIR / "screenshots"
REPOSITORIES_DIR = TMP_DIR / "repositories"
PROJECTS_DIR = TMP_DIR / "projects"


def _get_cache_key(path: Path, *args: Hashable, **kwargs: Hashable) -> str:
    hash = hashlib.md5()  # noqa: S324
    with open(path, "rb") as source_file:
        hash.update(source_file.read())
    hash.update(f"{args}-{kwargs}".encode())
    return f"{hash.hexdigest()}.svg"


def screenshot(  # noqa: D103
    board: str,
    size: tuple[int, int] = (80, 24),
    press: tuple[str] = (),
    env: tuple[tuple[str, str], ...] = (),
) -> str:
    path = Path("docs/examples", board).with_suffix(".py")
    SCREENSHOT_CACHE.mkdir(exist_ok=True)

    screenshot_path = SCREENSHOT_CACHE / _get_cache_key(path, size, press, env)
    if screenshot_path.exists():
        return screenshot_path.read_text()

    os.environ["PROJECTS_DIR"] = str(PROJECTS_DIR)
    for (var, val) in env:
        os.environ[var] = val
    try:
        app = Devboard(board=path, background_tasks=False)
        with Capture.STDOUT.here():
            svg = take_svg_screenshot(app=app, terminal_size=size, press=press)
        screenshot_path.write_text(svg)
        return svg
    finally:
        os.environ.pop("PROJECTS_DIR")
        for (var, _) in env:
            os.environ.pop(var)
