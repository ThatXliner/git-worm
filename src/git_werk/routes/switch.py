from pathlib import Path

import rich

from git_werk.config import load_config
from xclif import command


@command()
def _(branch: str) -> None:
    """Print the path to a worktree.

    BRANCH is the name of the worktree to switch to.
    """
    repo = _find_repo_root()
    config = load_config(repo / ".git-werk.toml")
    worktree_dir = config.worktree_dir if config else ".worktrees"
    wt_path = repo / worktree_dir / branch

    if not wt_path.exists():
        rich.print(f"[bold red]Error:[/bold red] No worktree found for [bold]{branch}[/bold]")
        return 1

    rich.print(f"Worktree for [bold]{branch}[/bold] @ [bold]{wt_path}[/bold]")


def _find_repo_root() -> Path:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())
