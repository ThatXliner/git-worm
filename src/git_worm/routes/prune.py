import subprocess
from pathlib import Path
from typing import Annotated

import rich

from git_worm.worktree import find_repo_root, is_merged, list_worktrees, remove_worktree
from xclif import Option, command


@command()
def _(
    merged: Annotated[bool, Option(description="Also remove worktrees whose branches are fully merged into main")] = False,
    dry_run: Annotated[bool, Option(description="Show what would be done without making any changes")] = False,
    yes: Annotated[bool, Option(name="yes", description="Skip confirmation prompt")] = False,
) -> None:
    """Remove stale worktree administrative files.

    Runs `git worktree prune` to clean up refs for worktrees that have
    been deleted manually without using `git worm rm`.
    """
    if dry_run:
        result = subprocess.run(
            ["git", "worktree", "prune", "--verbose", "--dry-run", "--expire=now"],
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                rich.print(f"[bold yellow]dry-run:[/bold yellow] Would prune: {line}")
        else:
            rich.print("[dim]Nothing to prune.[/dim]")

        if merged:
            _prune_merged(dry_run=True, yes=True)
        return

    # Collect what would be pruned
    stale_result = subprocess.run(
        ["git", "worktree", "prune", "--verbose", "--dry-run", "--expire=now"],
        check=True,
        capture_output=True,
        text=True,
    )
    stale_lines = stale_result.stderr.strip().splitlines() if stale_result.stderr.strip() else []

    merged_worktrees: list[dict] = []
    if merged:
        repo = find_repo_root()
        worktrees = list_worktrees()
        for wt in worktrees[1:]:
            branch = wt.get("branch")
            if branch and is_merged(branch, cwd=repo):
                merged_worktrees.append(wt)

    if not stale_lines and not merged_worktrees:
        if not merged and any(
            is_merged(wt["branch"], cwd=find_repo_root())
            for wt in list_worktrees()[1:]
            if wt.get("branch")
        ):
            rich.print("[dim]Nothing to prune. You have merged worktrees — run with [bold]--merged[/bold] to remove them.[/dim]")
        else:
            rich.print("[dim]Nothing to prune.[/dim]")
        return

    # Show what will be removed
    if stale_lines:
        rich.print("[bold]Stale worktree refs:[/bold]")
        for line in stale_lines:
            rich.print(f"  [dim]{line}[/dim]")
    if merged_worktrees:
        rich.print("[bold]Merged worktrees:[/bold]")
        for wt in merged_worktrees:
            rich.print(f"  [bold]{wt['branch']}[/bold] [dim]{wt['path']}[/dim]")

    if not yes:
        rich.print()
        confirm = input("Prune the above? [y/N] ").strip().lower()
        if confirm != "y":
            rich.print("[dim]Aborted.[/dim]")
            return

    pruned_stale = []
    if stale_lines:
        subprocess.run(["git", "worktree", "prune", "--verbose", "--expire=now"], check=True, capture_output=True, text=True)
        pruned_stale = stale_lines

    pruned_merged = []
    for wt in merged_worktrees:
        path = Path(wt["path"])
        remove_worktree(path)
        pruned_merged.append(wt)

    if pruned_stale or pruned_merged:
        rich.print(f"[bold green]Pruned ({len(pruned_stale) + len(pruned_merged)})[/bold green]")
        for line in pruned_stale:
            rich.print(f"  [red]-[/red] [dim]{line}[/dim]")
        for wt in pruned_merged:
            rich.print(f"  [red]-[/red] [bold]{wt['branch']}[/bold]")
    else:
        rich.print("[dim]Nothing pruned.[/dim]")
