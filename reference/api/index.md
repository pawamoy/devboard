# devboard

Devboard package.

A development dashboard for your projects.

Classes:

- **`Checkbox`** – A checkbox, added to rows to make them selectable.
- **`Column`** – A Devboard column.
- **`DataTable`** – A Devboard data table.
- **`Devboard`** – The Devboard application.
- **`Modal`** – A modal screen.
- **`ModalMixin`** – Mixin class to add a modal method.
- **`NotifyMixin`** – Mixin class to add notify methods.
- **`Project`** – A class representing development projects.
- **`Row`** – A Devboard row.
- **`SelectableRow`** – A selectable row.
- **`SelectableRowsDataTable`** – Data table with selectable rows.
- **`Status`** – Git status data.

Functions:

- **`get_parser`** – Return the CLI argument parser.
- **`main`** – Run the main program.

## Checkbox

```
Checkbox(checked: bool = False)
```

A checkbox, added to rows to make them selectable.

Methods:

- **`check`** – Uncheck the checkbox.
- **`toggle`** – Toggle the checkbox.
- **`uncheck`** – Uncheck the checkbox.

Attributes:

- **`checked`** (`bool`) – Whether the checkbox is checked.

### checked

```
checked: bool = False
```

Whether the checkbox is checked.

### check

```
check() -> None
```

Uncheck the checkbox.

Source code in `src/devboard/_internal/datatable.py`

```
def check(self) -> None:
    """Uncheck the checkbox."""
    self.checked = True
```

### toggle

```
toggle() -> bool
```

Toggle the checkbox.

Source code in `src/devboard/_internal/datatable.py`

```
def toggle(self) -> bool:
    """Toggle the checkbox."""
    self.checked = not self.checked
    return self.checked
```

### uncheck

```
uncheck() -> None
```

Uncheck the checkbox.

Source code in `src/devboard/_internal/datatable.py`

```
def uncheck(self) -> None:
    """Uncheck the checkbox."""
    self.checked = False
```

## Column

Bases: `Container`, `ModalMixin`, `NotifyMixin`

A Devboard column.

Methods:

- **`action_apply`** – Apply an action to selected rows.
- **`apply`** – Apply action on given row.
- **`compose`** – Compose column widgets.
- **`list_projects`** – List projects for this column.
- **`modal`** – Push a modal.
- **`notify_error`** – Notify error.
- **`notify_info`** – Notify information.
- **`notify_success`** – Notify success.
- **`notify_warning`** – Notify warning.
- **`on_mount`** – Fill data table.
- **`populate_rows`** – Populate rows for this column.
- **`update`** – Update the column (recompute data).

Attributes:

- **`DEFAULT_CLASSES`** – Textual CSS classes.
- **`HEADERS`** (`tuple[str, ...]`) – The data table headers.
- **`THREADED`** (`bool`) – Whether actions of this column should run in the background.
- **`TITLE`** (`str`) – The title of the column.
- **`app`** (`App`) – Textual application.
- **`table`** (`DataTable`) – Data table.

### DEFAULT_CLASSES

```
DEFAULT_CLASSES = 'box'
```

Textual CSS classes.

### HEADERS

```
HEADERS: tuple[str, ...] = ()
```

The data table headers.

### THREADED

```
THREADED: bool = True
```

Whether actions of this column should run in the background.

### TITLE

```
TITLE: str = ''
```

The title of the column.

### app

```
app: App
```

Textual application.

### table

```
table: DataTable
```

Data table.

### action_apply

```
action_apply(action: str = 'default') -> None
```

Apply an action to selected rows.

Source code in `src/devboard/_internal/board.py`

```
def action_apply(self, action: str = "default") -> None:
    """Apply an action to selected rows."""
    selected_rows = list(self.table.selected_rows) or [self.table.current_row]
    if self.THREADED:
        for row in selected_rows:
            self.run_worker(partial(self.apply, action=action, row=row), thread=True)  # type: ignore[arg-type]
    else:
        for row in selected_rows:
            self.apply(action=action, row=row)  # type: ignore[arg-type]
```

### apply

```
apply(action: str, row: Row) -> None
```

Apply action on given row.

Source code in `src/devboard/_internal/board.py`

```
def apply(self, action: str, row: Row) -> None:  # noqa: ARG002
    """Apply action on given row."""
    return
```

### compose

```
compose() -> ComposeResult
```

Compose column widgets.

Source code in `src/devboard/_internal/board.py`

```
def compose(self) -> ComposeResult:
    """Compose column widgets."""
    yield Static("▶ " + self.TITLE, classes="column-title")
    yield DataTable(id="table")
```

### list_projects

```
list_projects() -> Iterable[Project]
```

List projects for this column.

Source code in `src/devboard/_internal/board.py`

```
def list_projects(self) -> Iterable[Project]:
    """List projects for this column."""
    return ()
```

### modal

```
modal(text: str) -> None
```

Push a modal.

Source code in `src/devboard/_internal/modal.py`

```
def modal(self, text: str) -> None:
    """Push a modal."""
    self.app.push_screen(Modal(text=text))
```

### notify_error

```
notify_error(message: str, timeout: float = 3.0) -> None
```

Notify error.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_error(self, message: str, timeout: float = 3.0) -> None:
    """Notify error."""
    self.app.notify(f"[b red]ERROR[/]  {message}", severity="error", timeout=timeout)
```

### notify_info

```
notify_info(message: str, timeout: float = 3.0) -> None
```

Notify information.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_info(self, message: str, timeout: float = 3.0) -> None:
    """Notify information."""
    self.app.notify(f"[b blue]INFO[/]  {message}", severity="information", timeout=timeout)
```

### notify_success

```
notify_success(message: str, timeout: float = 3.0) -> None
```

Notify success.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_success(self, message: str, timeout: float = 3.0) -> None:
    """Notify success."""
    self.app.notify(f"[b green]SUCCESS[/]  {message}", severity="information", timeout=timeout)
```

### notify_warning

```
notify_warning(message: str, timeout: float = 3.0) -> None
```

Notify warning.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_warning(self, message: str, timeout: float = 3.0) -> None:
    """Notify warning."""
    self.app.notify(f"[b yellow]WARNING[/]  {message}", severity="warning", timeout=timeout)
```

### on_mount

```
on_mount() -> None
```

Fill data table.

Source code in `src/devboard/_internal/board.py`

```
def on_mount(self) -> None:
    """Fill data table."""
    self.update()
```

### populate_rows

```
populate_rows(project: Project) -> list[tuple[Any, ...]]
```

Populate rows for this column.

Source code in `src/devboard/_internal/board.py`

```
@staticmethod
def populate_rows(project: Project) -> list[tuple[Any, ...]]:  # noqa: ARG004
    """Populate rows for this column."""
    return []
```

### update

```
update() -> None
```

Update the column (recompute data).

Source code in `src/devboard/_internal/board.py`

```
def update(self) -> None:
    """Update the column (recompute data)."""
    table = self.query_one(DataTable)
    if table.loading:
        return
    table.loading = True
    table.clear(columns=True)
    table.cursor_type = "row"
    self._load_data(table)
```

## DataTable

Bases: `SelectableRowsDataTable`

A Devboard data table.

Methods:

- **`action_reverse_select`** – Reverse selection.
- **`action_toggle_select_all`** – Toggle-select all rows.
- **`action_toggle_select_down`** – Toggle selection down.
- **`action_toggle_select_row`** – Toggle-select current row.
- **`action_toggle_select_up`** – Toggle selection up.
- **`add_rows`** – Add rows.
- **`clear`** – Clear rows and optionally columns.
- **`force_refresh`** – Force refresh table.

Attributes:

- **`BINDINGS`** (`ClassVar`) – Key bindings for selecting rows.
- **`ROW`** – The class to instantiate rows.
- **`current_row`** (`SelectableRow`) – Currently selected row.
- **`selectable_rows`** (`Iterator[SelectableRow]`) – Rows, as selectable ones.
- **`selected_rows`** (`Iterator[SelectableRow]`) – Selected rows.

### BINDINGS

```
BINDINGS: ClassVar = [
    Binding(
        "space",
        "toggle_select_row",
        "Toggle select",
        show=False,
    ),
    Binding(
        "ctrl+a, *",
        "toggle_select_all",
        "Toggle select all",
        show=False,
    ),
    Binding(
        "exclamation_mark",
        "reverse_select",
        "Reverse select",
        show=False,
    ),
    Binding(
        "shift+up",
        "toggle_select_up",
        "Expand select up",
        show=False,
    ),
    Binding(
        "shift+down",
        "toggle_select_down",
        "Expand select down",
        show=False,
    ),
]
```

Key bindings for selecting rows.

### ROW

```
ROW = Row
```

The class to instantiate rows.

### current_row

```
current_row: SelectableRow
```

Currently selected row.

### selectable_rows

```
selectable_rows: Iterator[SelectableRow]
```

Rows, as selectable ones.

### selected_rows

```
selected_rows: Iterator[SelectableRow]
```

Selected rows.

### action_reverse_select

```
action_reverse_select() -> None
```

Reverse selection.

Source code in `src/devboard/_internal/datatable.py`

```
def action_reverse_select(self) -> None:
    """Reverse selection."""
    for row in self.selectable_rows:
        row.toggle_select()
    self.force_refresh()
```

### action_toggle_select_all

```
action_toggle_select_all() -> None
```

Toggle-select all rows.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_all(self) -> None:
    """Toggle-select all rows."""
    rows = list(self.selectable_rows)
    if all(row.selected for row in rows):
        for row in rows:
            row.unselect()
    else:
        for row in rows:
            row.select()
    self.force_refresh()
```

### action_toggle_select_down

```
action_toggle_select_down() -> None
```

Toggle selection down.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_down(self) -> None:
    """Toggle selection down."""
    try:
        row = self.current_row
        next_row = row.next
    except CellDoesNotExist:
        pass
    else:
        next_row.toggle_select()
        self.move_cursor(row=next_row.index)
        self.force_refresh()
```

### action_toggle_select_row

```
action_toggle_select_row() -> None
```

Toggle-select current row.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_row(self) -> None:
    """Toggle-select current row."""
    try:
        row = self.current_row
    except CellDoesNotExist:
        return
    row.toggle_select()
    self.force_refresh()
```

### action_toggle_select_up

```
action_toggle_select_up() -> None
```

Toggle selection up.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_up(self) -> None:
    """Toggle selection up."""
    try:
        row = self.current_row
        previous_row = row.previous
    except CellDoesNotExist:
        pass
    else:
        previous_row.toggle_select()
        self.move_cursor(row=previous_row.index)
        self.force_refresh()
```

### add_rows

```
add_rows(rows: Iterable[Iterable]) -> list[RowKey]
```

Add rows.

Automatically insert a column with checkboxes in position 0.

Source code in `src/devboard/_internal/datatable.py`

```
def add_rows(self, rows: Iterable[Iterable]) -> list[RowKey]:
    """Add rows.

    Automatically insert a column with checkboxes in position 0.
    """
    return super().add_rows((Checkbox(), *row) for row in rows)
```

### clear

```
clear(columns: bool = True) -> SelectableRowsDataTable
```

Clear rows and optionally columns.

When clearing columns, automatically re-add a column for checkboxes.

Source code in `src/devboard/_internal/datatable.py`

```
def clear(self, columns: bool = True) -> SelectableRowsDataTable:  # noqa: FBT001,FBT002
    """Clear rows and optionally columns.

    When clearing columns, automatically re-add a column for checkboxes.
    """
    super().clear(columns)
    if columns:
        self.add_column("", key="checkbox")
    return self
```

### force_refresh

```
force_refresh() -> None
```

Force refresh table.

Source code in `src/devboard/_internal/datatable.py`

```
def force_refresh(self) -> None:
    """Force refresh table."""
    # HACK: Without such increment, the table is refreshed
    # only when focus changes to another column.
    self._update_count += 1
    self.refresh()
```

## Devboard

```
Devboard(
    *args: Any,
    board: str | Path | None = None,
    background_tasks: bool = True,
    **kwargs: Any,
)
```

Bases: `App`, `ModalMixin`

The Devboard application.

Methods:

- **`action_exit`** – Exit application.
- **`action_refresh`** – Refresh all columns.
- **`action_show_help`** – Show help.
- **`compose`** – Compose the layout.
- **`fetch_all`** – Run git fetch in all projects, in background.
- **`modal`** – Push a modal.
- **`on_mount`** – Run background tasks.

Attributes:

- **`BINDINGS`** (`ClassVar`) – Application key bindings.
- **`CSS_PATH`** – Path to the CSS file.
- **`app`** (`App`) – Textual application.

Source code in `src/devboard/_internal/app.py`

```
def __init__(
    self,
    *args: Any,
    board: str | Path | None = None,
    background_tasks: bool = True,
    **kwargs: Any,
) -> None:
    """Initialize the app."""
    super().__init__(*args, **kwargs)
    self._board = board
    self._config_file = Path(user_config_dir(), "devboard", "config.toml")
    self._background_tasks = background_tasks
```

### BINDINGS

```
BINDINGS: ClassVar = [
    Binding("F5, ctrl+r", "refresh", "Refresh"),
    Binding("question_mark", "show_help", "Help"),
    Binding(
        "ctrl+q, q, escape", "exit", "Exit", key_display="Q"
    ),
]
```

Application key bindings.

### CSS_PATH

```
CSS_PATH = parent / 'devboard.tcss'
```

Path to the CSS file.

### app

```
app: App
```

Textual application.

### action_exit

```
action_exit() -> None
```

Exit application.

Source code in `src/devboard/_internal/app.py`

```
def action_exit(self) -> None:
    """Exit application."""
    self.workers.cancel_all()
    self.exit()
```

### action_refresh

```
action_refresh() -> None
```

Refresh all columns.

Source code in `src/devboard/_internal/app.py`

```
def action_refresh(self) -> None:
    """Refresh all columns."""
    for column in self.query(Column):
        column.update()
```

### action_show_help

```
action_show_help() -> None
```

Show help.

Source code in `src/devboard/_internal/app.py`

```
def action_show_help(self) -> None:
    """Show help."""
    lines = ["# Main keys\n\n"]
    lines.extend(self._bindings_help(Devboard))
    lines.extend(self._bindings_help(DataTable, search_up=True))
    for column in self.query(Column):
        lines.append(f"\n\n# {column.__class__.TITLE}\n\n")
        lines.extend(self._bindings_help(column.__class__))
    self.push_screen(Modal(text=Markdown("\n".join(lines))))
```

### compose

```
compose() -> ComposeResult
```

Compose the layout.

Source code in `src/devboard/_internal/app.py`

```
def compose(self) -> ComposeResult:
    """Compose the layout."""
    for column in self._load_columns():
        if isinstance(column, Column):
            yield column
        else:
            yield column()
    yield Footer()
```

### fetch_all

```
fetch_all() -> None
```

Run `git fetch` in all projects, in background.

Source code in `src/devboard/_internal/app.py`

```
@work(thread=True)
def fetch_all(self) -> None:
    """Run `git fetch` in all projects, in background."""
    projects = set()
    for column in self.query(Column):
        projects |= set(column.list_projects())
    with Pool() as pool:
        for project in projects:
            pool.apply_async(project.fetch)
```

### modal

```
modal(text: str) -> None
```

Push a modal.

Source code in `src/devboard/_internal/modal.py`

```
def modal(self, text: str) -> None:
    """Push a modal."""
    self.app.push_screen(Modal(text=text))
```

### on_mount

```
on_mount() -> None
```

Run background tasks.

Source code in `src/devboard/_internal/app.py`

```
def on_mount(self) -> None:
    """Run background tasks."""
    if self._background_tasks:
        self.fetch_all()
```

## Modal

```
Modal(*args: Any, text: Any, **kwargs: Any)
```

Bases: `ModalScreen`

A modal screen.

Methods:

- **`compose`** – Screen composition.
- **`on_key`** – Dismiss on any unbound key.

Attributes:

- **`text`** – Text content.

Source code in `src/devboard/_internal/modal.py`

```
def __init__(self, *args: Any, text: Any, **kwargs: Any) -> None:
    """Initialize the screen."""
    super().__init__(*args, **kwargs)
    if isinstance(text, str):
        self.text = Text.from_ansi(text)
        """Text content."""
    else:
        self.text = text
```

### text

```
text = from_ansi(text)
```

Text content.

### compose

```
compose() -> ComposeResult
```

Screen composition.

Source code in `src/devboard/_internal/modal.py`

```
def compose(self) -> ComposeResult:
    """Screen composition."""
    yield VerticalScroll(Static(self.text), id="modal-contents")
```

### on_key

```
on_key(event: Key) -> None
```

Dismiss on any unbound key.

Source code in `src/devboard/_internal/modal.py`

```
def on_key(self, event: Key) -> None:
    """Dismiss on any unbound key."""
    if not any(bindings.keys.get(event.key) for _, bindings in self.app._modal_binding_chain):  # type: ignore[attr-defined]
        self.dismiss()
```

## ModalMixin

Mixin class to add a modal method.

Methods:

- **`modal`** – Push a modal.

Attributes:

- **`app`** (`App`) – Textual application.

### app

```
app: App
```

Textual application.

### modal

```
modal(text: str) -> None
```

Push a modal.

Source code in `src/devboard/_internal/modal.py`

```
def modal(self, text: str) -> None:
    """Push a modal."""
    self.app.push_screen(Modal(text=text))
```

## NotifyMixin

Mixin class to add notify methods.

Methods:

- **`notify_error`** – Notify error.
- **`notify_info`** – Notify information.
- **`notify_success`** – Notify success.
- **`notify_warning`** – Notify warning.

Attributes:

- **`app`** (`App`) – Textual application.

### app

```
app: App
```

Textual application.

### notify_error

```
notify_error(message: str, timeout: float = 3.0) -> None
```

Notify error.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_error(self, message: str, timeout: float = 3.0) -> None:
    """Notify error."""
    self.app.notify(f"[b red]ERROR[/]  {message}", severity="error", timeout=timeout)
```

### notify_info

```
notify_info(message: str, timeout: float = 3.0) -> None
```

Notify information.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_info(self, message: str, timeout: float = 3.0) -> None:
    """Notify information."""
    self.app.notify(f"[b blue]INFO[/]  {message}", severity="information", timeout=timeout)
```

### notify_success

```
notify_success(message: str, timeout: float = 3.0) -> None
```

Notify success.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_success(self, message: str, timeout: float = 3.0) -> None:
    """Notify success."""
    self.app.notify(f"[b green]SUCCESS[/]  {message}", severity="information", timeout=timeout)
```

### notify_warning

```
notify_warning(message: str, timeout: float = 3.0) -> None
```

Notify warning.

Source code in `src/devboard/_internal/notifications.py`

```
def notify_warning(self, message: str, timeout: float = 3.0) -> None:
    """Notify warning."""
    self.app.notify(f"[b yellow]WARNING[/]  {message}", severity="warning", timeout=timeout)
```

## Project

```
Project(path: Path)
```

A class representing development projects.

It is instantiated with a path, and then provides many utility properties and methods.

Methods:

- **`checkout`** – Checkout branch, restore previous one when exiting.
- **`delete`** – Delete branch.
- **`fetch`** – Fetch.
- **`lock`** – Lock project.
- **`pull`** – Pull branch.
- **`push`** – Push branch.
- **`unlock`** – Unlock project.
- **`unpulled`** – Number of unpulled commits, per branch.
- **`unpushed`** – Number of unpushed commits, per branch.
- **`unreleased`** – List unreleased commits.

Attributes:

- **`DEFAULT_BRANCHES`** (`tuple[str, ...]`) – Name of common default branches. Mainly useful to compute unreleased commits.
- **`LOCKS`** (`dict[Project, Lock]`) – Locks for projects, to avoid concurrent operations.
- **`branch`** (`Head`) – Currently checked out branch.
- **`default_branch`** (`str`) – Default branch (or main branch), as checked out when cloning.
- **`is_dirty`** (`bool`) – Whether the project is in a "dirty" state (uncommitted modifications).
- **`latest_tag`** (`TagReference`) – Latest tag.
- **`name`** (`str`) – Name of the project.
- **`path`** (`Path`) – Path of the project on the file-system.
- **`repo`** (`Repo`) – GitPython's Repo object.
- **`status`** (`Status`) – Status of the project.
- **`status_line`** (`str`) – Status of the project, as a string.

### DEFAULT_BRANCHES

```
DEFAULT_BRANCHES: tuple[str, ...] = ('main', 'master')
```

Name of common default branches. Mainly useful to compute unreleased commits.

### LOCKS

```
LOCKS: dict[Project, Lock] = defaultdict(Lock)
```

Locks for projects, to avoid concurrent operations.

### branch

```
branch: Head
```

Currently checked out branch.

### default_branch

```
default_branch: str
```

Default branch (or main branch), as checked out when cloning.

### is_dirty

```
is_dirty: bool
```

Whether the project is in a "dirty" state (uncommitted modifications).

### latest_tag

```
latest_tag: TagReference
```

Latest tag.

### name

```
name: str
```

Name of the project.

### path

```
path: Path
```

Path of the project on the file-system.

### repo

```
repo: Repo
```

GitPython's `Repo` object.

### status

```
status: Status
```

Status of the project.

### status_line

```
status_line: str
```

Status of the project, as a string.

### checkout

```
checkout(branch: str | None) -> Iterator[None]
```

Checkout branch, restore previous one when exiting.

Source code in `src/devboard/_internal/projects.py`

```
@contextmanager
def checkout(self, branch: str | None) -> Iterator[None]:
    """Checkout branch, restore previous one when exiting."""
    if not branch:
        yield
        return
    current = self.branch
    if branch == current:
        yield
        return
    self.repo.branches[branch].checkout()
    try:
        yield
    finally:
        current.checkout()
```

### delete

```
delete(branch: str) -> None
```

Delete branch.

Source code in `src/devboard/_internal/projects.py`

```
def delete(self, branch: str) -> None:
    """Delete branch."""
    self.repo.delete_head(branch, force=True)
```

### fetch

```
fetch() -> None
```

Fetch.

Source code in `src/devboard/_internal/projects.py`

```
def fetch(self) -> None:
    """Fetch."""
    with suppress(AttributeError, GitCommandError):
        self.repo.remotes.origin.fetch()
    with suppress(AttributeError, GitCommandError):
        self.repo.remotes.upstream.fetch()
```

### lock

```
lock() -> bool
```

Lock project.

Source code in `src/devboard/_internal/projects.py`

```
def lock(self) -> bool:
    """Lock project."""
    return self.LOCKS[self].acquire(blocking=False)
```

### pull

```
pull(branch: str | None = None) -> None
```

Pull branch.

Source code in `src/devboard/_internal/projects.py`

```
def pull(self, branch: str | None = None) -> None:
    """Pull branch."""
    with self.checkout(branch):
        self.repo.remotes.origin.pull()
```

### push

```
push(branch: str | None = None) -> None
```

Push branch.

Source code in `src/devboard/_internal/projects.py`

```
def push(self, branch: str | None = None) -> None:
    """Push branch."""
    with self.checkout(branch):
        self.repo.remotes.origin.push()
```

### unlock

```
unlock() -> None
```

Unlock project.

Source code in `src/devboard/_internal/projects.py`

```
def unlock(self) -> None:
    """Unlock project."""
    self.LOCKS[self].release()
```

### unpulled

```
unpulled(remote: str = 'origin') -> dict[str, int]
```

Number of unpulled commits, per branch.

Source code in `src/devboard/_internal/projects.py`

```
def unpulled(self, remote: str = "origin") -> dict[str, int]:
    """Number of unpulled commits, per branch."""
    result = {}
    for branch in self.repo.branches:
        with contextlib.suppress(GitCommandError):
            result[branch.name] = len(list(self.repo.iter_commits(f"{branch.name}..{remote}/{branch.name}")))
    return result
```

### unpushed

```
unpushed(remote: str = 'origin') -> dict[str, int]
```

Number of unpushed commits, per branch.

Source code in `src/devboard/_internal/projects.py`

```
def unpushed(self, remote: str = "origin") -> dict[str, int]:
    """Number of unpushed commits, per branch."""
    result = {}
    for branch in self.repo.branches:
        with contextlib.suppress(GitCommandError):
            result[branch.name] = len(list(self.repo.iter_commits(f"{remote}/{branch.name}..{branch.name}")))
    return result
```

### unreleased

```
unreleased(branch: str | None = None) -> list[Commit]
```

List unreleased commits.

Source code in `src/devboard/_internal/projects.py`

```
def unreleased(self, branch: str | None = None) -> list[Commit]:
    """List unreleased commits."""
    commits = []
    if branch is None:
        try:
            branch = self.default_branch
        except ValueError:
            return []
    iterator = self.repo.iter_commits(branch)
    try:
        latest_tagged_commit = self.latest_tag.commit
    except IndexError:
        return list(iterator)
    for commit in iterator:
        if commit == latest_tagged_commit:
            break
        commits.append(commit)
    return commits
```

## Row

```
Row(table: SelectableRowsDataTable, key: RowKey)
```

Bases: `SelectableRow`

A Devboard row.

Methods:

- **`remove`** – Remove row from the table.
- **`select`** – Select this row.
- **`toggle_select`** – Toggle-select this row.
- **`unselect`** – Unselect this row.

Attributes:

- **`app`** (`App`) – Textual application.
- **`checkbox`** (`Checkbox`) – Row checkbox.
- **`data`** (`list`) – Row data (without checkbox).
- **`index`** (`int`) – Row index.
- **`key`** (`RowKey`) – The row key.
- **`next`** (`SelectableRow`) – Next row (down).
- **`previous`** (`SelectableRow`) – Previous row (up).
- **`project`** (`Project`) – Devboard project.
- **`selected`** (`bool`) – Whether this row is selected.
- **`table`** (`SelectableRowsDataTable`) – The data table containing this row.

### app

```
app: App
```

Textual application.

### checkbox

```
checkbox: Checkbox
```

Row checkbox.

### data

```
data: list
```

Row data (without checkbox).

### index

```
index: int
```

Row index.

### key

```
key: RowKey
```

The row key.

### next

```
next: SelectableRow
```

Next row (down).

### previous

```
previous: SelectableRow
```

Previous row (up).

### project

```
project: Project
```

Devboard project.

### selected

```
selected: bool
```

Whether this row is selected.

### table

```
table: SelectableRowsDataTable
```

The data table containing this row.

### remove

```
remove() -> None
```

Remove row from the table.

Source code in `src/devboard/_internal/datatable.py`

```
def remove(self) -> None:
    """Remove row from the table."""
    self.table.remove_row(self.key)
```

### select

```
select() -> None
```

Select this row.

Source code in `src/devboard/_internal/datatable.py`

```
def select(self) -> None:
    """Select this row."""
    self.checkbox.check()
```

### toggle_select

```
toggle_select() -> bool
```

Toggle-select this row.

Source code in `src/devboard/_internal/datatable.py`

```
def toggle_select(self) -> bool:
    """Toggle-select this row."""
    return self.checkbox.toggle()
```

### unselect

```
unselect() -> None
```

Unselect this row.

Source code in `src/devboard/_internal/datatable.py`

```
def unselect(self) -> None:
    """Unselect this row."""
    self.checkbox.uncheck()
```

## SelectableRow

```
SelectableRow(table: SelectableRowsDataTable, key: RowKey)
```

A selectable row.

Methods:

- **`remove`** – Remove row from the table.
- **`select`** – Select this row.
- **`toggle_select`** – Toggle-select this row.
- **`unselect`** – Unselect this row.

Attributes:

- **`app`** (`App`) – Textual application.
- **`checkbox`** (`Checkbox`) – Row checkbox.
- **`data`** (`list`) – Row data (without checkbox).
- **`index`** (`int`) – Row index.
- **`key`** (`RowKey`) – The row key.
- **`next`** (`SelectableRow`) – Next row (down).
- **`previous`** (`SelectableRow`) – Previous row (up).
- **`selected`** (`bool`) – Whether this row is selected.
- **`table`** (`SelectableRowsDataTable`) – The data table containing this row.

### app

```
app: App
```

Textual application.

### checkbox

```
checkbox: Checkbox
```

Row checkbox.

### data

```
data: list
```

Row data (without checkbox).

### index

```
index: int
```

Row index.

### key

```
key: RowKey
```

The row key.

### next

```
next: SelectableRow
```

Next row (down).

### previous

```
previous: SelectableRow
```

Previous row (up).

### selected

```
selected: bool
```

Whether this row is selected.

### table

```
table: SelectableRowsDataTable
```

The data table containing this row.

### remove

```
remove() -> None
```

Remove row from the table.

Source code in `src/devboard/_internal/datatable.py`

```
def remove(self) -> None:
    """Remove row from the table."""
    self.table.remove_row(self.key)
```

### select

```
select() -> None
```

Select this row.

Source code in `src/devboard/_internal/datatable.py`

```
def select(self) -> None:
    """Select this row."""
    self.checkbox.check()
```

### toggle_select

```
toggle_select() -> bool
```

Toggle-select this row.

Source code in `src/devboard/_internal/datatable.py`

```
def toggle_select(self) -> bool:
    """Toggle-select this row."""
    return self.checkbox.toggle()
```

### unselect

```
unselect() -> None
```

Unselect this row.

Source code in `src/devboard/_internal/datatable.py`

```
def unselect(self) -> None:
    """Unselect this row."""
    self.checkbox.uncheck()
```

## SelectableRowsDataTable

Bases: `DataTable`

Data table with selectable rows.

Methods:

- **`action_reverse_select`** – Reverse selection.
- **`action_toggle_select_all`** – Toggle-select all rows.
- **`action_toggle_select_down`** – Toggle selection down.
- **`action_toggle_select_row`** – Toggle-select current row.
- **`action_toggle_select_up`** – Toggle selection up.
- **`add_rows`** – Add rows.
- **`clear`** – Clear rows and optionally columns.
- **`force_refresh`** – Force refresh table.

Attributes:

- **`BINDINGS`** (`ClassVar`) – Key bindings for selecting rows.
- **`ROW`** – The class to instantiate selectable rows.
- **`current_row`** (`SelectableRow`) – Currently selected row.
- **`selectable_rows`** (`Iterator[SelectableRow]`) – Rows, as selectable ones.
- **`selected_rows`** (`Iterator[SelectableRow]`) – Selected rows.

### BINDINGS

```
BINDINGS: ClassVar = [
    Binding(
        "space",
        "toggle_select_row",
        "Toggle select",
        show=False,
    ),
    Binding(
        "ctrl+a, *",
        "toggle_select_all",
        "Toggle select all",
        show=False,
    ),
    Binding(
        "exclamation_mark",
        "reverse_select",
        "Reverse select",
        show=False,
    ),
    Binding(
        "shift+up",
        "toggle_select_up",
        "Expand select up",
        show=False,
    ),
    Binding(
        "shift+down",
        "toggle_select_down",
        "Expand select down",
        show=False,
    ),
]
```

Key bindings for selecting rows.

### ROW

```
ROW = SelectableRow
```

The class to instantiate selectable rows.

### current_row

```
current_row: SelectableRow
```

Currently selected row.

### selectable_rows

```
selectable_rows: Iterator[SelectableRow]
```

Rows, as selectable ones.

### selected_rows

```
selected_rows: Iterator[SelectableRow]
```

Selected rows.

### action_reverse_select

```
action_reverse_select() -> None
```

Reverse selection.

Source code in `src/devboard/_internal/datatable.py`

```
def action_reverse_select(self) -> None:
    """Reverse selection."""
    for row in self.selectable_rows:
        row.toggle_select()
    self.force_refresh()
```

### action_toggle_select_all

```
action_toggle_select_all() -> None
```

Toggle-select all rows.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_all(self) -> None:
    """Toggle-select all rows."""
    rows = list(self.selectable_rows)
    if all(row.selected for row in rows):
        for row in rows:
            row.unselect()
    else:
        for row in rows:
            row.select()
    self.force_refresh()
```

### action_toggle_select_down

```
action_toggle_select_down() -> None
```

Toggle selection down.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_down(self) -> None:
    """Toggle selection down."""
    try:
        row = self.current_row
        next_row = row.next
    except CellDoesNotExist:
        pass
    else:
        next_row.toggle_select()
        self.move_cursor(row=next_row.index)
        self.force_refresh()
```

### action_toggle_select_row

```
action_toggle_select_row() -> None
```

Toggle-select current row.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_row(self) -> None:
    """Toggle-select current row."""
    try:
        row = self.current_row
    except CellDoesNotExist:
        return
    row.toggle_select()
    self.force_refresh()
```

### action_toggle_select_up

```
action_toggle_select_up() -> None
```

Toggle selection up.

Source code in `src/devboard/_internal/datatable.py`

```
def action_toggle_select_up(self) -> None:
    """Toggle selection up."""
    try:
        row = self.current_row
        previous_row = row.previous
    except CellDoesNotExist:
        pass
    else:
        previous_row.toggle_select()
        self.move_cursor(row=previous_row.index)
        self.force_refresh()
```

### add_rows

```
add_rows(rows: Iterable[Iterable]) -> list[RowKey]
```

Add rows.

Automatically insert a column with checkboxes in position 0.

Source code in `src/devboard/_internal/datatable.py`

```
def add_rows(self, rows: Iterable[Iterable]) -> list[RowKey]:
    """Add rows.

    Automatically insert a column with checkboxes in position 0.
    """
    return super().add_rows((Checkbox(), *row) for row in rows)
```

### clear

```
clear(columns: bool = True) -> SelectableRowsDataTable
```

Clear rows and optionally columns.

When clearing columns, automatically re-add a column for checkboxes.

Source code in `src/devboard/_internal/datatable.py`

```
def clear(self, columns: bool = True) -> SelectableRowsDataTable:  # noqa: FBT001,FBT002
    """Clear rows and optionally columns.

    When clearing columns, automatically re-add a column for checkboxes.
    """
    super().clear(columns)
    if columns:
        self.add_column("", key="checkbox")
    return self
```

### force_refresh

```
force_refresh() -> None
```

Force refresh table.

Source code in `src/devboard/_internal/datatable.py`

```
def force_refresh(self) -> None:
    """Force refresh table."""
    # HACK: Without such increment, the table is refreshed
    # only when focus changes to another column.
    self._update_count += 1
    self.refresh()
```

## Status

```
Status(
    added: list[Path],
    deleted: list[Path],
    modified: list[Path],
    renamed: list[Path],
    typechanged: list[Path],
    untracked: list[Path],
)
```

Git status data.

Attributes:

- **`added`** (`list[Path]`) – Added files.
- **`deleted`** (`list[Path]`) – Deleted files.
- **`modified`** (`list[Path]`) – Modified files.
- **`renamed`** (`list[Path]`) – Renamed files.
- **`typechanged`** (`list[Path]`) – Type-changed files.
- **`untracked`** (`list[Path]`) – Untracked files.

### added

```
added: list[Path]
```

Added files.

### deleted

```
deleted: list[Path]
```

Deleted files.

### modified

```
modified: list[Path]
```

Modified files.

### renamed

```
renamed: list[Path]
```

Renamed files.

### typechanged

```
typechanged: list[Path]
```

Type-changed files.

### untracked

```
untracked: list[Path]
```

Untracked files.

## get_parser

```
get_parser() -> ArgumentParser
```

Return the CLI argument parser.

Returns:

- `ArgumentParser` – An argparse parser.

Source code in `src/devboard/_internal/cli.py`

```
def get_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser.

    Returns:
        An argparse parser.
    """
    parser = argparse.ArgumentParser(prog="devboard")
    parser.add_argument("--show-config-dir", action="store_true", help="Show Devboard's configuration directory.")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {debug._get_version()}")
    parser.add_argument("--debug-info", action=_DebugInfo, help="Print debug information.")
    parser.add_argument("board", nargs="?", default=None, help="Board name or path.")
    return parser
```

## main

```
main(args: list[str] | None = None) -> int
```

Run the main program.

This function is executed when you type `devboard` or `python -m devboard`.

Parameters:

- **`args`** (`list[str] | None`, default: `None` ) – Arguments passed from the command line.

Returns:

- `int` – An exit code.

Source code in `src/devboard/_internal/cli.py`

```
def main(args: list[str] | None = None) -> int:
    """Run the main program.

    This function is executed when you type `devboard` or `python -m devboard`.

    Parameters:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    parser = get_parser()
    opts = parser.parse_args(args=args)
    if opts.show_config_dir:
        print(user_config_dir(appname="devboard"))
        return 0
    app = Devboard(board=opts.board)
    app.run()
    return 0
```
