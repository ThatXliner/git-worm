import rich
from rich.tree import Tree

from git_werk.worktree import list_worktrees, is_dirty, is_merged
from xclif import command

from pathlib import Path


@command("list")
def _() -> None:
    """List all worktrees."""
    worktrees = list_worktrees()

    if not worktrees:
        rich.print("[dim]No worktrees found.[/dim]")
        return

    tree = Tree("[bold]Worktrees[/bold]")
    for wt in worktrees:
        path = wt["path"]
        branch = wt.get("branch", wt.get("head", "???")[:8])
        is_bare = wt.get("bare") == "true"
        is_detached = wt.get("detached") == "true"

        if is_bare:
            label = f"[dim]{path}[/dim] [italic](bare)[/italic]"
        elif is_detached:
            label = f"[bold]{branch}[/bold] [dim]{path}[/dim] [yellow](detached)[/yellow]"
        else:
            dirty = is_dirty(Path(path))
            merged = is_merged(branch)
            status = ""
            if dirty:
                status += " [red]*dirty*[/red]"
            if merged:
                status += " [green](merged)[/green]"
            label = f"[bold]{branch}[/bold] [dim]{path}[/dim]{status}"

        tree.add(label)

    rich.print(tree)
