---
title: Overview
hide:
- feedback
---

--8<-- "README.md"

## Usage

Devboard displays columns stacked horizontally, like a Kanban board.
Each column is a "To Do Something" and presents information in a data table.
Data tables have a header line with labels, and multiple rows
presenting information collected from source items. An item can be a project,
an issue, a pull request, or an object from another provider.
The default board uses Git projects and collects their status, commits,
branches, and tags.

Press ++ctrl+r++ to scan all columns again. On the default Git board, ++ctrl+shift+r++ fetches remote data before scanning each project.

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

### Keyboard controls

Boards keep these default shortcuts unless they override the same keys. Custom boards can add shortcuts and column actions.

| Key | Action |
| --- | --- |
| `?` | Show help for the current board |
| ++ctrl+k++ | Show or hide the Keys panel |
| ++ctrl+p++ | Open the command palette |
| ++ctrl+c++ or ++escape++ | Exit from the main board |
| ++ctrl+r++ | Refresh all columns |
| ++ctrl+f5++ | Force-refresh all columns |
| ++ctrl+f++ | Filter all columns |
| ++ctrl+e++ | Collapse or expand the focused column |
| ++ctrl+x++ | Maximize the focused column or restore its previous layout |

The Keys panel includes shortcuts hidden from the footer and updates when focus changes. The command palette also provides item refresh, column refresh, their forced versions, and **Filter column**, without default shortcuts.

In the filter prompt, press ++enter++ to apply the text or ++escape++ to cancel. Submit empty text to clear the filter. The default filter searches displayed cells and ignores case.

| Navigation key | Action |
| --- | --- |
| ++tab++ / ++shift+tab++ | Move focus forward / backward between widgets, including collapsed columns |
| ++up++ / ++down++ | Move the row cursor |
| ++left++ / ++right++ | Scroll the table horizontally |
| ++page-up++ / ++page-down++ | Move the row cursor by a page |
| ++ctrl+home++ / ++ctrl+end++ | Move to the first / last row |
| ++home++ / ++end++ | Scroll to the left / right edge of the table |

Use ++space++ to toggle a row's checkbox. Pressing ++enter++ emits Textual's row-selection event, which the default board does not handle.

Default application shortcuts leave unmodified letters available for custom board and column actions. Special characters such as `?`, `*`, and `!` have built-in bindings. See the [tutorial](tutorial.md#keyboard-controls) to customize bindings.

The default Git board adds these actions in the focused column:

| Column | Key | Action |
| --- | --- | --- |
| To Commit | ++s++ | Show Git status |
| To Commit | ++d++ | Show Git diff |
| To Pull | ++p++ | Pull the branch from `origin`; blocked if the project has uncommitted changes |
| To Pull | ++d++ | Force-delete the local branch without a confirmation prompt |
| To Push | ++p++ | Push the branch to `origin` |

The **To Release** column has no additional shortcuts.

### Informative actions

Once your board displays some rows in the "To Commit" column,
try showing the Git status or diff with ++s++ and ++d++ keys.

```python exec="1" html="1" session="screenshots-usage"
print(screenshot("columns/commit_pull_push_release", size=(100, 24), press=("down", "s")))
```

You can scroll using the mouse wheel and the arrows.
Press ++escape++ or any unbound key to close the dialog.

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

Column actions apply to selected visible rows in the focused column. If no visible rows are selected, actions use the current row. Hidden rows retain their selections but do not participate in actions.

- To select a row, press ++space++. To unselect it, press ++space++ again.
- To select all visible rows, press ++ctrl+a++ or `*`. If all visible rows are selected, this clears their selection.
- To reverse the selection of visible rows, press `!`.
- Press ++shift+up++ or ++shift+down++ to move to the previous or next row and toggle that row's selection.


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
