import subprocess
from pathlib import Path
from typing import Annotated

import rich

from git_worm.worktree import find_repo_root, list_worktrees, remove_worktree
from xclif import Option, command


@command()
def _(
    merged: Annotated[bool, Option(description="Also remove worktrees whose branches are fully merged into main")] = False,
    dry_run: Annotated[bool, Option(description="Show what would be done without making any changes")] = False,
) -> None:
    """Remove stale worktree administrative files.

    Runs `git worktree prune` to clean up refs for worktrees that have
    been deleted manually without using `git worm rm`.
    """
    if dry_run:
        result = subprocess.run(
            ["git", "worktree", "prune", "--verbose", "--dry-run"],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                rich.print(f"[bold yellow]dry-run:[/bold yellow] Would prune: {line}")
        else:
            rich.print("[dim]Nothing to prune.[/dim]")
    else:
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

    if merged:
        _prune_merged(dry_run=dry_run)


def _prune_merged(*, dry_run: bool = False) -> None:
    """Remove worktrees whose branches are fully merged into the main branch."""
    repo = find_repo_root()
    worktrees = list_worktrees()

    # Find the main branch name (first worktree is the primary one)
    if not worktrees:
        return
    main_branch = worktrees[0].get("branch")
    if not main_branch:
        return

    # Get branches merged into the main branch
    result = subprocess.run(
        ["git", "branch", "--merged", main_branch],
        check=True,
        capture_output=True,
        text=True,
    )
    merged_branches = {
        line.strip().lstrip("*+ ")
        for line in result.stdout.splitlines()
        if not line.startswith("*")
    }

    pruned = False
    for wt in worktrees[1:]:  # skip the primary worktree
        branch = wt.get("branch")
        if not branch or branch not in merged_branches:
            continue
        path = Path(wt["path"])
        if dry_run:
            rich.print(f"[bold yellow]dry-run:[/bold yellow] Would remove merged worktree [bold]{branch}[/bold] @ [dim]{path}[/dim]")
        else:
            remove_worktree(path)
            rich.print(f"[bold green]Removed merged worktree[/bold green] [bold]{branch}[/bold]")
        pruned = True

    if not pruned:
        rich.print("[dim]No merged worktrees to remove.[/dim]")
