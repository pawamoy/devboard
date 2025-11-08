---
hide:
- navigation
---

# Tutorial

```python exec="1"
# Create repositories in temporary directory.
--8<-- "docs/examples/repositories.py"
create_repositories()
```

```python exec="1" session="screenshots-tutorial"
# Load `screenshot` function in screenshots session.
--8<-- "docs/examples/screenshot.py"
```

In this tutorial, we will rebuild the board provided by default.
It is an initiation to board building, and should give you enough
understanding of boards are built so that you can build your own.

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit_pull_push_release", size=(100, 20)))
```

The default board has four columns:

- **To Commit**: a column showing projects that have uncommitted modifications.
    Keeping modifications locally is risky: they are not saved anywhere
    and you could lose them if something happens to your disk or computer.
    Modifications that have been sitting here for a long time should be
    committed with a "wip" message (Work In Progress) to a properly named branch,
    then pushed to a remote.
- **To Pull**: a column showing project branches that have commits in the remote.
    Keep your branches up-to-date to avoid having Git error out when you try to push.
- **To Push**: a column showing project branches that have local commits not in the remote.
    Push your commits to avoid losing your work.
- **To Release**: a column showing projects that have unreleased commits (commits that
    are more recent than the most recent tag). Maybe it's time to release these
    changes so that your users can benefit from them?

By default, Devboard looks for the board configuration
in your user config directory, for example:

- `~/.config/devboard` on Linux systems, following the XDG specification
- `~/Library/Preferences/devboard` on Mac OS
- `C:\Users\<username>\AppData\Local\devboard\devboard`
    or `C:\Users\<username>\AppData\Roaming\devboard\devboard` on Windows

Use `devboard --show-config-dir` to print your configuration directory path.

When you run `devboard` the first time,
it creates a default board called `default.py`.
For the tutorial, we will create a new file next to it
and call it `tutorial.py`.

```bash
touch "$(devboard --show-config-dir)/tutorial.py"
```

We will also tell Devboard to use this tutorial board by default.
Open the `config.toml` file in the config directory,
and change the board value to "tutorial":

```toml
board = "tutorial"
```

Now open the `tutorial.py` file in your favorite editor,
and you'll be ready to start building.

## Building the "To Commit" column

In this column, we want to show a list of rows that display
the project name and a summary of the changes in the project.

- `A` for added files
- `D` for deleted files
- `M` for modified files
- `R` for renamed/moved files
- `T` for files whose type changed
- `U` for untracked (new) files

We also want to add key bindings to show the output
of `git status` and `git diff` on projects.

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit", size=(60, 16)))
```

### Creating a column, adding it to the board

First, we create the column and add it to the board:

```python
from devboard import Column


class ToCommit(Column):
    TITLE = "To Commit"


columns = [
    ToCommit,
]
```

Here we create a column by declaring a class that inherits from [`devboard.Column`][].
Then we add it to the `columns` list, because Devboard uses this variable to build the board.

### Listing projects for a column

Running `devboard` now shows our "To Commit" column, but it is empty.
We will tell Devboard how to find the relevant projects for this column
by implementing a `list_project` method on the class:

```python hl_lines="1 2 8-12"
from pathlib import Path
from devboard import Column, Project


class ToCommit(Column):
    TITLE = "To Commit"

    def list_projects(self):
        base_dir = Path.home() / "dev"
        for filedir in base_dir.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield Project(filedir)

columns = [
    ToCommit,
]
```

Here we set our base directory, where our projects are, to the `dev` folder
in our home/user directory. You should change that line to use the directory
in which your projects actually are.
Then we iterate on the files/directories within this base directory,
and only keep the ones that repositories: they are directories and they
have a `.git` folder inside.
We yield instances of [`devboard.Project`][], because that's what Devboard expects.

### Populating rows of columns' data tables

Great, now Devboard can find our projects.
But running `devboard` still shows an empty column.
Of course, it doesn't know what to do with these projects.
We will tell it how to scan a project to add rows to our table
by implementing the `populate_rows` method.

```python hl_lines="7 15-17"
from pathlib import Path
from devboard import Column, Project


class ToCommit(Column):
    TITLE = "To Commit"
    HEADERS = ("Project", "Details")

    def list_projects(self):
        base_dir = Path.home() / "dev"
        for filedir in base_dir.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield Project(filedir)

    @staticmethod
    def populate_rows(project):
        return [(project, project.status_line)] if project.is_dirty else []


columns = [
    ToCommit,
]
```

We declare the table headers with the `HEADERS` class variable.

Then we build and return rows in the `populate_rows` method.
The number of element in each row must be equal to the number of headers.
Fortunately, the status line functionality is built into [`devboard.Project`][],
so we can use it directly. We don't bother computing a status line
if the project is not "dirty", i.e. has no current modifications.

You may have noticed that the method is a `staticmethod`.
This is required by Devboard for technical reasons that are beyond this tutorial's scope.

Devboard is now able to show you a table of projects and status lines.
If the column still shows up empty, try to create a few files in your projects,
so that Devboard has something to show. You can of course delete these files
once you made sure the column is working.

### Adding keybindings

Now lets add some key bindings to our column.
We want to show the output of `git status` when hitting ++s++,
and the output of `git diff` when hitting ++d++.
We do that by declaring the `BINDINGS` class variable,
and by implementing the `apply` method:

```python hl_lines="2 8-12 24-29"
from pathlib import Path
from devboard import Column, Project, Row


class ToCommit(Column):
    TITLE = "To Commit"
    HEADERS = ("Project", "Details")
    THREADED = False
    BINDINGS = [
        ("s", "apply('status')", "Show status"),
        ("d", "apply('diff')", "Show diff"),
    ]

    def list_projects(self):
        base_dir = Path.home() / "dev"
        for filedir in base_dir.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield Project(filedir)

    @staticmethod
    def populate_rows(project):
        return [(project, project.status_line)] if project.is_dirty else []

    def apply(self, action, row):
        if action == "status":
            self.modal(text=row.project.repo.git(c="color.status=always").status())
        if action == "diff":
            self.modal(text=row.project.repo.git(c="color.ui=always").diff())
        raise ValueError(f"Unknown action '{action}'")```


columns = [
    ToCommit,
]
```

Bindings are a list of a 3-tuples.

1. In the first item of the tuple, we write the key we want to bind.
    For multiple keys, separate them with commas.
2. In the second item, we tell Devboard to apply a specific action,
    for example `apply('status')` to apply a "status" action.
3. In the third item, we write the description of the binding.
    It will appear in the footer, next to the keys you chose.

The `BINDINGS` variable is directly used by Textual:
see [their Bindings documentation](https://textual.textualize.io/guide/input/#bindings)
for more information.

Next, we write our `apply` method, that takes an `action` (a string),
and a [`devboard.Row`][] instance.
This row instance has a `project` attribute that returns the [`devboard.Project`][]
instance that we added to the row in `populate_rows`.
The project itself has a `repo` attribute that returns a `Repo` object
from the [GitPython](https://gitpython.readthedocs.io/en/stable/) library.
We use its `git` attribute to run Git commands in the project.
For more information on these objects, see GitPython's
[API Reference](https://gitpython.readthedocs.io/en/stable/reference.html).
Finally, we pass the output of the Git command to [`self.modal()`][devboard.Column.modal],
which shows a modal window on the screen with the specified contents.

Hitting ++s++ should show the output of `git status`:

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit", size=(100, 24), press=("down", "s")))
```

Hitting ++d++ should show the output of `git diff`:

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit", size=(100, 24), press=("d")))
```

Because we don't want to apply actions in parallel,
but rather stack the modals on top of each other,
sequentially, we set the `THREADED` class variable to `False`.
The next columns will apply actions that run in the background,
so they will leave `THREADED` to its default value, `True`.

That's it for the "To Commit" column, now to the next!

## Building the "To Pull" column

In this column, we want to show a list of rows that display the project name,
a Git branch, and the number of commits that can be pulled from the remote
for that branch.

We also want to add key bindings to run `git pull` on the given
project and branch, or to delete the given branch in the project
when it's already merged or is not needed anymore.

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/pull", size=(60, 16)))
```

We create the column, directly implemeting its `list_projects` method:

```python
class ToPull(Column):
    TITLE = "To Pull"

    def list_projects(self):
        base_dir = Path.home() / "dev"
        for filedir in base_dir.iterdir():
            if filedir.is_dir() and filedir.joinpath(".git").is_dir():
                yield Project(filedir)
```

We are starting to repeat ourselves here.
If all columns list the same projects, we could move this code
in a reusable function:

```python hl_lines="1 3-6 13"
BASE_DIR = Path.home() / "dev"

def list_projects():
    for filedir in BASE_DIR.iterdir():
        if filedir.is_dir() and filedir.joinpath(".git").is_dir():
            yield Project(filedir)


class ToPull(Column):
    TITLE = "To Pull"

    def list_projects(self):
        yield from list_projects()
```

If needed, update the `list_projects` method of the `ToCommit` column too.

Now lets implement the `populate_rows` method:

```python hl_lines="3 8-10"
class ToPull(Column):
    TITLE = "To Pull"
    HEADERS = ("Project", "Branch", "Commits")

    def list_projects(self):
        yield from list_projects()

    @staticmethod
    def populate_rows(project: Project):
        return [(project, branch, commits) for branch, commits in project.unpulled().items() if commits]
```

Fortunately again, Devboard projects have this functionality built-in,
so it is easy to count the number of commits to be pulled per branch of a project.

### Actions running in the background, locking projects

We can declare our bindings and our `apply` method:

```python hl_lines="1 7-10 19-36"
from git import GitCommandError


class ToPull(Column):
    TITLE = "To Pull"
    HEADERS = ("Project", "Branch", "Commits")
    BINDINGS = [
        ("p", "apply('pull')", "Pull"),
        ("d", "apply('delete')", "Delete branch"),
    ]

    def list_projects(self):
        yield from list_projects()

    @staticmethod
    def populate_rows(project):
        return [(project, branch, commits) for branch, commits in project.unpulled().items() if commits]

    def apply(self, action, row):
        project, branch, _ = row.data
        message = f"Pulling branch [i]{branch}[/] in [i]{project}[/]"
        if not project.lock():
            self.notify_warning(f"Prevented: {message}: An operation is ongoing")
            return
        if not project.is_dirty:
            self.notify_info(f"Started: {message}")
            try:
                project.pull(branch)
            except GitCommandError as error:
                self.notify_error(f"{message}: {error}", timeout=10)
            else:
                self.notify_success(f"Finished: {message}")
                row.remove()
        else:
            self.notify_warning(f"Prevented: {message}: project is dirty")
        project.unlock()
```

When applying an action on a row (project and branch),
we want to catch any error that happens.
For this we import `GitCommandError` from `git`,
to use it in `except` blocks.

In our `apply` method, we start by getting the project and branch
from the current row. It is done by unpacking the row's data.
We also prepare our notification message.
It uses [Rich markup](https://rich.readthedocs.io/en/stable/markup.html).

Since Devboard allows to select multiple rows
and apply an action to all selected rows in the background,
we want to make sure that we don't try and run
a Git command that could change the state of a project,
*while another column is already running such a command*.
In short, to prevent race conditions, we want to "lock" projects:
only one action can be applied on each project at a time.
Other columns trying to apply an action on a locked project
will notify the user with a warning message.

To lock our project, we use [`project.lock()`][devboard.Project.lock].
It it fails, it means the project was already locked,
and we notify the user with a warning message.
If it succeeds, we can continue and apply our action.

Here we don't bother checking projects that are dirty,
because it would not be safe to switch to other branches
and/or pull commits from the remote repository.

Since pulling commits can take a few seconds or more,
we notify the user that we started the command.
We then use [`project.pull()`][devboard.Project.pull], once again built into
Devboard projects, to pull a given branch.
If we catch an error, we notify the user with an error message.
This message is displayed for a longer time, 10 seconds,
to let the user read it.
If all went well, we notify the user with a success message,
and we remove the row from the board.

Finally, and this is very important, we unlock the project.

Lets add our new column to the board:

```python hl_lines="3"
columns = [
    ToCommit,
    ToPull,
]
```

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit_pull", size=(100, 20), press=("tab")))
```

## Building the "To Push" column

This column is similar to the "To Pull" column,
except we want to show unpushed commits instead
of commits to pull.

We will add a key binding to push the commits,
but not to delete branches.
If there are commits to push, it is be preferable to push them
rather than deleting the branch.

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/push", size=(60, 16)))
```

There is nothing new here, we can write the entire class at once:

```python
class ToPush(Column):
    TITLE = "To Push"
    HEADERS = ("Project", "Branch", "Commits")
    BINDINGS = [
        ("p", "apply('push')", "Push"),
    ]

    def list_projects(self):
        yield from list_projects()

    @staticmethod
    def populate_rows(project):
        return [(project, branch, commits) for branch, commits in project.unpushed().items() if commits]

    def apply(self, action, row):
        project, branch, _ = row.data
        message = f"Pushing branch [i]{branch}[/] in [i]{project}[/]"
        if not project.lock():
            self.notify_warning(f"Prevented: {message}: An operation is ongoing")
            return
        self.notify_info(f"Started: {message}")
        try:
            project.push(branch)
        except GitCommandError as error:
            self.notify_error(f"{message}: {error}", timeout=10)
        else:
            self.notify_success(f"Finished: {message}")
            row.remove()
        project.unlock()
```

Lets add our new column to the board:

```python hl_lines="4"
columns = [
    ToCommit,
    ToPull,
    ToPush,
]
```

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit_pull_push", size=(100, 20), press=("tab",) * 2))
```

## Building the "To Release" column

In the last column, we want to show projects
that have unreleased changes, for example
bug fixes and features.
Each one will display the project name,
and a summary line with a number for each type of change.

- `F` for feature
- `X` for bug fix
- `R` for refactor
- `B` for build configuration or packaging
- `D` for changes in dependencies

To be able to infer the type of commits,
we suppose that projects rely on the
[conventional commit convention](https://www.conventionalcommits.org/en/v1.0.0/).
Commit messages are prefixed with `type:`, type being `feat`, `fix`, etc.

We could add a binding here to automatically release a new version
of a project, but we leave this as an exercise to the reader,
because releasing a new version should be done carefully anyway
(reviewing the set of commits that will be released,
reviewing the changelog and the choosing the new version number, etc.).

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/release", size=(60, 16)))
```

Again, nothing new here, lets write the entire class at once:

```python
class ToRelease(Column):
    TITLE = "To Release"
    HEADERS = ("Project", "Details")

    def list_projects(self):
        yield from list_projects()

    @staticmethod
    def populate_rows(project):
        commit_types = {"feat": "F", "fix": "X", "refactor": "R", "build": "B", "deps": "D"}
        by_type = {commit_type: 0 for commit_type in commit_types}
        for commit in project.unreleased():
            for commit_type in commit_types:
                if commit.summary.startswith(f"{commit_type}:"):
                    by_type[commit_type] += 1
        parts = [f"{by_type[ct]}{commit_types[ct]}" for ct in commit_types if by_type[ct]]
        if parts:
            return [(project, " ".join(parts))]
        return []
```

Devboard projects have an `unreleased()` method that returns
the unreleased commits for a given branch.
We use it to iterate on unreleased commits, parsing the summary
of their message to infer the commit type.
We count each type, and if any type count is higher than 0,
we build a summary line and return a row.

Lets add our new column to the board:

```python hl_lines="5"
columns = [
    ToCommit,
    ToPull,
    ToPush,
    ToRelease,
]
```

Here is our final board with four columns:

```python exec="1" html="1" session="screenshots-tutorial"
print(screenshot("columns/commit_pull_push_release", size=(100, 20), press=("tab",) * 3))
```

Now you can continue tinkering with your board,
or delete your configuration file and re-run `devboard`
to recreate the default configuration.

That's it for the tutorial!
Next we recommend reading the guide, to learn more
about each aspect of Devboard features.
