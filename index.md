# Devboard

A development dashboard for your projects.

## Installation

```
pip install devboard
```

With [`uv`](https://docs.astral.sh/uv/):

```
uv tool install devboard
```

## Sponsors

## Usage

Devboard displays columns stacked horizontally, like a Kanban board. Each column is a "To Do Something" and presents information in a data table. Data tables have a header line with labels, and multiple rows presenting the information collected in your projects. Projects are supposed to be Git repositories from which we can collect information such as status, commits, branches, tags, etc.

To start using Devboard, try to run the `devboard` command in your terminal. It will show you a default board with four columns:

If the columns are empty and collapsed, that is normal. It's because Devboard does not know where to look for your projects. By default, it looks into the `dev` folder in your home/user directory. To change that directory, you can modify it directly in the default board, located in your user configuration directory (use `devboard --show-config-dir`), or you can set the `DEVBOARD_PROJECTS` environment variable:

```
export DEVBOARD_PROJECTS=~/path/to/your/projects
```

```
setx DEVBOARD_PROJECTS ~/path/to/your/projects
```

### Informative actions

Once your board displays some rows in the "To Commit" column, try showing the Git status or diff with `S` and `D` keys.

You can scroll using the mouse wheel and the arrows. You can dismiss the modal window with any other key press.

### Background actions

Try to move focus to different columns with the `Tab` and `Shift`+`Tab` keys. In the "To Pull" column, try to start a background action that will pull a branch using the `P` key. If action started successfully, you should see a notification:

Upon success, you'll see a success notification, and the row will be removed from the table:

If there is an error, you'll see an error notification:

Sometimes the column will prevent you from applying action, for example when the repository is dirty:

Devboard will also prevent applying multiple actions rapidly to the same project, to prevent race conditions:

### Row selection

You can select multiple rows and apply actions on all selected rows at once.

- To select a row, press `Space`. To unselect it, press `Space` again.
- To select all rows, press `Ctrl`+`A` or `Num *`.
- To reverse the selection, press `!`.
- To expand the selection upwards or downwards, hold `Shift` and press `Up` or `Down`.

## Building your own board

Follow our [tutorial](tutorial/)!

## Choosing boards

Boards in the configuration directory can be chosen by passing their name to the `devboard` command:

```
devboard myboard
```

You can set a board as the default one in Devboard's configuration file. Use `devboard --show-config-dir` to get its location, then:

```
board = "myboard"
```

Now when calling `devboard` it will use `myboard` instead of the `default` one.

Finally, you can also pass a path to a board module:

```
devboard ./path/to/myboard.py
```
