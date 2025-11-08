--8<-- "README.md"

## Usage

Devboard displays columns stacked horizontally, like a Kanban board.
Each column is a "To Do Something" and presents information in a data table.
Data tables have a header line with labels, and multiple rows
presenting the information collected in your projects.
Projects are supposed to be Git repositories from which we can collect information
such as status, commits, branches, tags, etc.

To start using Devboard, try to run the `devboard` command
in your terminal. It will show you a default board with four columns:

```python exec="1"
# Create repositories in temporary directory.
--8<-- "docs/examples/repositories.py"
create_repositories()
```

```python exec="1" session="screenshots-usage"
# Load `screenshot` function in screenshots session.
--8<-- "docs/examples/screenshot.py"
```

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/commit_pull_push_release", size=(100, 20)))
```

If the columns are empty and collapsed, that is normal.
It's because Devboard does not know where to look for your projects.
By default, it looks into the `dev` folder in your home/user directory.
To change that directory, you can modify it directly in the default board,
located in your user configuration directory (use `devboard --show-config-dir`),
or you can set the `DEVBOARD_PROJECTS` environment variable:

/// tab | Linux / Mac OS
```bash
export DEVBOARD_PROJECTS=~/path/to/your/projects
```
///

/// tab | Windows
```sh
setx DEVBOARD_PROJECTS ~/path/to/your/projects
```
///

### Informative actions

Once your board displays some rows in the "To Commit" column,
try showing the Git status or diff with ++s++ and ++d++ keys.

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/commit_pull_push_release", size=(100, 24), press=("down", "s")))
```

You can scroll using the mouse wheel and the arrows.
You can dismiss the modal window with any other key press.

### Background actions

Try to move focus to different columns with the ++tab++ and ++shift+tab++ keys.
In the "To Pull" column, try to start a background action
that will pull a branch using the ++p++ key.
If action started successfully, you should see a notification:

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/notify", size=(100, 24), press=("tab", "down", "p"), env=(("msgtype", "started"),)))
```

Upon success, you'll see a success notification,
and the row will be removed from the table:

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/notify", size=(100, 24), press=("tab", "down", "p"), env=(("msgtype", "finished"),)))
```

If there is an error, you'll see an error notification:

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/notify", size=(100, 24), press=("tab", "down", "p"), env=(("msgtype", "error"),)))
```

Sometimes the column will prevent you from applying action,
for example when the repository is dirty:

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/notify", size=(100, 24), press=("tab", "p")))
```

Devboard will also prevent applying multiple actions rapidly
to the same project, to prevent race conditions:

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/notify", size=(100, 24), press=("tab", "down", "p"), env=(("msgtype", "ongoing"),)))
```

### Row selection

You can select multiple rows and apply actions on all selected rows at once.

- To select a row, press ++space++. To unselect it, press ++space++ again.
- To select all rows, press ++ctrl+a++ or ++num-asterisk++.
- To reverse the selection, press ++exclam++.
- To expand the selection upwards or downwards, hold ++shift++ and press ++up++ or ++down++.


```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/commit_pull_push_release", size=(100, 24), press=("space", "down", "space")))
```

## Building your own board

Follow our [tutorial](tutorial.md)!

## Choosing boards

Boards in the configuration directory can be chosen
by passing their name to the `devboard` command:

```bash
devboard myboard
```

You can set a board as the default one in Devboard's configuration file.
Use `devboard --show-config-dir` to get its location, then:

```toml
board = "myboard"
```

Now when calling `devboard` it will use `myboard` instead of the `default` one.

Finally, you can also pass a path to a board module:

```bash
devboard ./path/to/myboard.py
```