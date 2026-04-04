import subprocess

import rich

from xclif import command


@command()
def _() -> None:
    """Remove stale worktree administrative files.

    Runs `git worktree prune` to clean up refs for worktrees that have
    been deleted manually without using `git werk rm`.
    """
    result = subprocess.run(
        ["git", "worktree", "prune", "--verbose"],
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            rich.print(f"[dim]pruned:[/dim] {line}")
    else:
        rich.print("[dim]Nothing to prune.[/dim]")
