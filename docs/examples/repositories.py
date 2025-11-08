import subprocess
from pathlib import Path
from tempfile import gettempdir
from textwrap import dedent

TMP_DIR = Path(gettempdir(), "devboard")
REPOSITORIES_DIR = TMP_DIR / "repositories"
PROJECTS_DIR = TMP_DIR / "projects"


def _sh(directory: Path, script: str) -> None:
    subprocess.run(["sh", "-c", dedent(script)], cwd=directory, capture_output=True, check=True)  # noqa: S603, S607

def _prepare(name: str, remote: str, local: str = "", post_remote: str = "") -> None:
    repo = REPOSITORIES_DIR / name
    if not repo.exists():
        repo.mkdir(parents=True)
        _sh(repo, remote)
    project = PROJECTS_DIR / name
    if not project.exists():
        _sh(repo, f"git clone $(pwd) {project}")
        if local:
            _sh(project, local)
        if post_remote:
            _sh(repo, post_remote)
            _sh(project, "git fetch")


def create_repositories() -> None:  # noqa: D103
        _prepare(
            "archan",
            """
            git init .
            echo "# archan" > README.md
            git add -A
            git commit -m "chore: Initial commit"
            """,
            """
            echo "Analysis of your architecture strength based on DSM data." >> README.md
            """,
        )
        _prepare(
            "dependenpy",
            """
            git init .
            echo "# dependenpy" > README.md
            touch pyproject.toml
            git add -A
            git commit -m "chore: Initial commit"
            """,
            """
            rm pyproject.toml
            touch detect_cycles.py
            touch standard_lib.py
            """,
        )
        _prepare(
            "git-changelog",
            """
            git init .
            echo "# git-changelog" > README.md
            git add -A
            git commit -m "chore: Initial commit"
            """,
            "",
            """
            echo "Automatic Changelog generator using Jinja2 templates." >> README.md
            git commit -am "docs: Add description"
            """,
        )
        _prepare(
            "failprint",
            """
            git init .
            echo "# failprint" > README.md
            git add -A
            git commit -m "chore: Initial commit"
            git switch -c feat/capture-fd
            mkdir -p src/failprint
            touch src/failprint/__init__.py
            git add -A
            git commit -m "refactor: Prepare capture feature"
            git switch main
            """,
            """
            git switch feat/capture-fd
            touch pyproject.toml
            """,
            """
            git switch feat/capture-fd
            touch src/failprint/capture.py
            git add -A
            git commit -m "feat: Capture output at the file descriptor level"
            """,
        )
        _prepare(
            "duty",
            """
            git init .
            echo "# failprint" > README.md
            git add -A
            git commit -m "chore: Initial commit"
            """,
            """
            mkdir -p src/duty
            touch src/duty/__init__.py
            git add -A
            git commit -m "feat: Implement prototype"
            touch src/duty/collection.py
            git add -A
            git commit -m "feat: Add collections"
            touch src/duty/decorator.py
            git add -A
            git commit -m "fix: Fix calling decorator with a single argument"
            """,
        )
        _prepare(
            "mvodb",
            """
            git init .
            echo "# failprint" > README.md
            git add -A
            git commit -m "chore: Initial commit"
            git tag 0.1.0
            mkdir -p src/mvodb
            touch src/mvodb/__init__.py
            git add -A
            git commit -m "feat: Implement prototype"
            """,
        )

