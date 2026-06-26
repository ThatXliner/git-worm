from pathlib import Path
from typing import Annotated

from git_worm.config import load_config
from git_worm.worktree import find_repo_root, find_worktree
from xclif import Arg, Option, WithConfig, command, console


@command()
def _(
    branch: Annotated[str, Arg(description="Name of the worktree to switch to")],
    worktree_dir: WithConfig[str] = ".worktrees",
    path: Annotated[bool, Option(description="Print only the worktree path")] = False,
) -> None:
    """Print the path to a worktree."""
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")
    if config and worktree_dir == ".worktrees":
        worktree_dir = config.worktree_dir
    wt = find_worktree(branch, cwd=repo)
    wt_path = Path(wt["path"]) if wt else repo / worktree_dir / branch

    if not wt_path.exists():
        console.print(f"[bold red]Error:[/bold red] No worktree found for [bold]{branch}[/bold]")
        return 1

    if path:
        print(wt_path)
        return

    console.print(f"Worktree for [bold]{branch}[/bold] @ [bold]{wt_path}[/bold]")
