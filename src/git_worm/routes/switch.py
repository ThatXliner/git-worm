from pathlib import Path

import rich

from git_worm.config import load_config
from git_worm.worktree import find_repo_root
from xclif import command


@command()
def _(branch: str) -> None:
    """Print the path to a worktree.

    BRANCH is the name of the worktree to switch to.
    """
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")
    worktree_dir = config.worktree_dir if config else ".worktrees"
    wt_path = repo / worktree_dir / branch

    if not wt_path.exists():
        rich.print(f"[bold red]Error:[/bold red] No worktree found for [bold]{branch}[/bold]")
        return 1

    rich.print(f"Worktree for [bold]{branch}[/bold] @ [bold]{wt_path}[/bold]")
