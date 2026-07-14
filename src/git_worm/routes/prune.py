import subprocess
from pathlib import Path
from typing import Annotated

from git_worm.worktree import find_repo_root, is_dirty, is_merged, list_worktrees, remove_worktree
from xclif import Option, command, console


def _collect_merged(repo: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Find worktrees whose branches are merged into the default branch.

    Returns (prunable, dirty) — dirty worktrees are merged but have
    uncommitted changes, so they are reported rather than removed.
    """
    prunable: list[dict[str, str]] = []
    dirty: list[dict[str, str]] = []
    for wt in list_worktrees(cwd=repo)[1:]:
        branch = wt.get("branch")
        path = Path(wt["path"])
        if not branch or not path.exists():
            continue
        if not is_merged(branch, cwd=repo):
            continue
        (dirty if is_dirty(path) else prunable).append(wt)
    return prunable, dirty


@command()
def _(
    no_merged: Annotated[bool, Option(name="no-merged", description="Only prune stale refs; keep worktrees whose branches are merged")] = False,
    dry_run: Annotated[bool, Option(description="Show what would be done without making any changes")] = False,
    yes: Annotated[bool, Option(name="yes", description="Skip confirmation prompt")] = False,
) -> None:
    """Remove stale worktree refs and merged worktrees.

    Runs `git worktree prune` to clean up refs for worktrees that have
    been deleted manually without using `git worm rm`, and removes
    worktrees whose branches are fully merged into the default branch
    (pass --no-merged to keep those).
    """
    repo = find_repo_root()

    stale_result = subprocess.run(
        ["git", "worktree", "prune", "--verbose", "--dry-run", "--expire=now"],
        check=True,
        capture_output=True,
        text=True,
    )
    stale_lines = stale_result.stderr.strip().splitlines() if stale_result.stderr.strip() else []

    merged_worktrees: list[dict[str, str]] = []
    dirty_merged: list[dict[str, str]] = []
    if not no_merged:
        merged_worktrees, dirty_merged = _collect_merged(repo)

    if not stale_lines and not merged_worktrees:
        if no_merged and _collect_merged(repo)[0]:
            console.print("[dim]Nothing to prune. You have merged worktrees — rerun without [bold]--no-merged[/bold] to remove them.[/dim]")
        else:
            for wt in dirty_merged:
                console.print(f"[yellow]Skipping merged worktree with uncommitted changes:[/yellow] [bold]{wt['branch']}[/bold] [dim]{wt['path']}[/dim]")
            console.print("[dim]Nothing to prune.[/dim]")
        return

    # Show what will be removed
    if stale_lines:
        console.print("[bold]Stale worktree refs:[/bold]")
        for line in stale_lines:
            console.print(f"  [dim]{line}[/dim]")
    if merged_worktrees:
        console.print("[bold]Merged worktrees:[/bold]")
        for wt in merged_worktrees:
            console.print(f"  [bold]{wt['branch']}[/bold] [dim]{wt['path']}[/dim]")
    for wt in dirty_merged:
        console.print(f"[yellow]Skipping merged worktree with uncommitted changes:[/yellow] [bold]{wt['branch']}[/bold] [dim]{wt['path']}[/dim]")

    if dry_run:
        console.print("[bold yellow]dry-run:[/bold yellow] no changes made.")
        return

    if not yes:
        console.print()
        confirm = input("Prune the above? [y/N] ").strip().lower()
        if confirm != "y":
            console.print("[dim]Aborted.[/dim]")
            return

    if stale_lines:
        subprocess.run(["git", "worktree", "prune", "--verbose", "--expire=now"], check=True, capture_output=True, text=True)
        for line in stale_lines:
            console.print(f"[dim]pruned:[/dim] {line}")

    for wt in merged_worktrees:
        path = Path(wt["path"])
        remove_worktree(path)
        console.print(f"[bold green]Removed merged worktree[/bold green] [bold]{wt['branch']}[/bold]")
