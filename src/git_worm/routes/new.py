from typing import Annotated

import rich
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from git_worm.config import load_config
from git_worm.files import copy_ignored_files
from git_worm.worktree import add_worktree, find_repo_root
from xclif import Arg, Option, WithConfig, command
from xclif.context import get_context

_ACTION_ICONS = {"copied": "+", "COW": "~", "symlinked": "->", "ignored": "x"}
_ACTION_COLORS = {"symlinked": "cyan", "COW": "magenta", "ignored": "dim"}


@command("new", "add")
def _(
    branch: Annotated[str, Arg(description="Branch name to check out (or create with --from)")],
    from_ref: Annotated[str, Option(name="from", description="Create branch from this ref")] = "",
    worktree_dir: WithConfig[str] = ".worktrees",
    *branches: str,
) -> None:
    """Create one or more new worktrees for branches."""
    all_branches = (branch, *branches)
    repo = find_repo_root()
    config = load_config(repo / ".git-worm.toml")

    failed = False
    for b in all_branches:
        wt_path = repo / worktree_dir / b

        if wt_path.exists():
            rich.print(f"[bold red]Error:[/bold red] Worktree already exists at [bold]{wt_path}[/bold]")
            failed = True
            continue

        # Create the worktree
        add_worktree(wt_path, b, from_ref=from_ref or None)

        # Ensure .worktrees/.gitignore exists
        wt_dir = repo / worktree_dir
        gitignore = wt_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")

        # Copy gitignored files with a live progress bar
        share_rules = config.share_rules if config else None

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]Copying files[/bold]"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[dim]{task.fields[current_file]}[/dim]"),
            transient=True,
        ) as progress:
            task = progress.add_task("copy", total=None, current_file="")

            def on_progress(completed: int, total: int, name: str, action: str) -> None:
                icon = _ACTION_ICONS.get(action, "+")
                progress.update(task, completed=completed, total=total, current_file=f"{icon} {name}")

            results = copy_ignored_files(repo, wt_path, share_rules=share_rules, on_progress=on_progress)

        # Print summary
        copied = [r for r in results if r["action"] != "ignored"]
        rich.print(f"[bold green]Created worktree[/bold green] [bold]{b}[/bold] @ [dim]{wt_path}[/dim]")
        if results and get_context().verbosity >= 1:
            if copied:
                rich.print(f"[dim]Copied {len(copied)} ignored file(s)[/dim]")
            for r in results:
                action = r["action"]
                name = r["name"]
                icon = _ACTION_ICONS.get(action, "+")
                color = _ACTION_COLORS.get(action, "green")
                if action == "ignored":
                    rich.print(f"  [dim]{icon} {name} ({action})[/dim]")
                else:
                    rich.print(f"  [{color}]{icon}[/{color}] {name} [dim]({action})[/dim]")

    if len(all_branches) == 1 and not failed:
        wt_path = repo / worktree_dir / all_branches[0]
        rich.print(f"[dim]Go to your new worktree with[/dim] [bold]cd {wt_path}[/bold]")

    if failed:
        return 1
