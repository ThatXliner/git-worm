from pathlib import Path

import rich

from git_worm.config import load_config
from git_worm.worktree import find_repo_root, is_dirty, remove_worktree
from xclif import command


@command()
def _(branch: str, force: bool = False) -> None:
    """Remove a worktree.

    BRANCH is the name of the worktree to remove.
    """
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")
    worktree_dir = config.worktree_dir if config else ".worktrees"
    wt_path = repo / worktree_dir / branch

    if not wt_path.exists():
        rich.print(f"[bold red]Error:[/bold red] No worktree found at [bold]{wt_path}[/bold]")
        return 1

    if not force and is_dirty(wt_path):
        rich.print(
            f"[bold yellow]Warning:[/bold yellow] Worktree [bold]{branch}[/bold] has uncommitted changes.\n"
            f"Use [bold]--force[/bold] to remove anyway."
        )
        return 1

    remove_worktree(wt_path, force=force)
    rich.print(f"[bold green]Removed worktree[/bold green] [bold]{branch}[/bold]")
