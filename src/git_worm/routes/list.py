import rich
from rich.console import Console
from rich.tree import Tree

from git_worm.worktree import list_worktrees, is_dirty, is_merged
from xclif import command

from pathlib import Path


@command("list", "ls")
def _() -> None:
    """List all worktrees."""
    worktrees = list_worktrees()

    if not worktrees:
        rich.print("[dim]No worktrees found.[/dim]")
        return

    repo_root = Path(worktrees[0]["path"])

    tree = Tree("[bold]Worktrees[/bold]")
    for i, wt in enumerate(worktrees):
        path = wt["path"]
        try:
            rel_path = Path(path).relative_to(repo_root)
            path_display = f"./{rel_path}"
        except ValueError:
            path_display = path

        branch = wt.get("branch", wt.get("head", "???")[:8])
        is_bare = wt.get("bare") == "true"
        is_detached = wt.get("detached") == "true"
        is_primary = i == 0

        if is_bare:
            label = f"[dim]{path_display}[/dim] [italic](bare)[/italic]"
        elif is_detached:
            label = f"[bold]{branch}[/bold] [dim]{path_display}[/dim] [yellow](detached)[/yellow]"
        elif not Path(path).exists():
            label = f"[bold]{branch}[/bold] [dim]{path_display}[/dim] [red](missing — run `git worm prune`)[/red]"
        else:
            dirty = is_dirty(Path(path))
            merged = is_merged(branch)
            status = ""
            if dirty:
                status += " [red][italic]dirty[/italic][/red]"
            if merged:
                status += " [green](merged)[/green]"
            branch_fmt = f"[bold blue]{branch}[/bold blue]" if is_primary else f"[bold]{branch}[/bold]"
            label = f"{branch_fmt} [dim]{path_display}[/dim]{status}"

        tree.add(label)

    console = Console(soft_wrap=False)
    console.print(tree)
