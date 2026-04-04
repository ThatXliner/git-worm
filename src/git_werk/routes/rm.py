from pathlib import Path

import rich

from git_werk.config import load_config
from git_werk.worktree import is_dirty, remove_worktree
from xclif import command


@command()
def _(branch: str, force: bool = False) -> None:
    """Remove a worktree.

    BRANCH is the name of the worktree to remove.
    """
    repo = _find_repo_root()
    config = load_config(repo / ".git-werk.toml")
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


def _find_repo_root() -> Path:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())
