from typing import Annotated

import rich

from git_worm.config import load_config
from git_worm.worktree import find_repo_root
from xclif import Arg, WithConfig, command


@command()
def _(
    branch: Annotated[str, Arg(description="Name of the worktree to switch to")],
    worktree_dir: WithConfig[str] = ".worktrees",
) -> None:
    """Print the path to a worktree."""
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")
    if config:
        worktree_dir = config.worktree_dir
    wt_path = repo / worktree_dir / branch

    if not wt_path.exists():
        rich.print(f"[bold red]Error:[/bold red] No worktree found for [bold]{branch}[/bold]")
        return 1

    rich.print(f"Worktree for [bold]{branch}[/bold] @ [bold]{wt_path}[/bold]")
