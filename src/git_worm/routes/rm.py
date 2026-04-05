from typing import Annotated

import rich

from git_worm.config import load_config
from git_worm.worktree import find_repo_root, is_dirty, remove_worktree
from xclif import Arg, Option, WithConfig, command


@command()
def _(
    branch: Annotated[str, Arg(description="Name of the worktree to remove")],
    force: Annotated[bool, Option(description="Remove even if the worktree has uncommitted changes")] = False,
    worktree_dir: WithConfig[str] = ".worktrees",
) -> None:
    """Remove a worktree."""
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")
    if config:
        worktree_dir = config.worktree_dir
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
