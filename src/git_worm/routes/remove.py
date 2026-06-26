from pathlib import Path
from typing import Annotated

from git_worm.config import load_config
from git_worm.worktree import find_repo_root, find_worktree, is_dirty, remove_worktree
from xclif import Arg, Option, WithConfig, command, console


@command("remove", "rm")
def _(
    branch: Annotated[str, Arg(description="Name of the worktree to remove")],
    force: Annotated[bool, Option(description="Remove even if the worktree has uncommitted changes")] = False,
    dry_run: Annotated[bool, Option(description="Show what would be done without making any changes")] = False,
    yes: Annotated[bool, Option(name="yes", description="Skip confirmation prompt")] = False,
    worktree_dir: WithConfig[str] = ".worktrees",
    *branches: str,
) -> None:
    """Remove one or more worktrees."""
    branches = (branch, *branches)
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")
    if config and worktree_dir == ".worktrees":
        worktree_dir = config.worktree_dir

    # First pass: validate and collect removable worktrees
    to_remove: list[tuple[str, "Path"]] = []
    failed = False
    for b in branches:
        wt = find_worktree(b, cwd=repo)
        wt_path = Path(wt["path"]) if wt else repo / worktree_dir / b

        if not wt_path.exists():
            console.print(f"[bold red]Error:[/bold red] No worktree found at [bold]{wt_path}[/bold]")
            failed = True
            continue

        if not force and is_dirty(wt_path):
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Worktree [bold]{b}[/bold] has uncommitted changes.\n"
                f"Use [bold]--force[/bold] to remove anyway."
            )
            failed = True
            continue

        to_remove.append((b, wt_path))

    if not to_remove:
        return 1 if failed else 0

    if dry_run:
        for b, wt_path in to_remove:
            console.print(f"[bold yellow]dry-run:[/bold yellow] Would remove worktree [bold]{b}[/bold] @ [dim]{wt_path}[/dim]")
        return 1 if failed else 0

    if not yes:
        console.print("[bold]Will remove:[/bold]")
        for b, wt_path in to_remove:
            console.print(f"  [bold]{b}[/bold] [dim]{wt_path}[/dim]")
        console.print()
        confirm = input("Remove the above? [y/N] ").strip().lower()
        if confirm != "y":
            console.print("[dim]Aborted.[/dim]")
            return

    for b, wt_path in to_remove:
        remove_worktree(wt_path, force=force)
        console.print(f"[bold green]Removed worktree[/bold green] [bold]{b}[/bold]")

    if failed:
        return 1
