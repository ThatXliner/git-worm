import subprocess
from typing import Annotated

import rich
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from xclif import Arg, Option, WithConfig, command
from xclif.context import get_context

from git_worm.config import load_config
from git_worm.files import (
    _default_strategy,
    _match_rule,
    copy_ignored_files,
    detect_package_manager,
    get_ignored_entries,
    should_skip_node_modules,
)
from git_worm.worktree import add_worktree, branch_exists, find_repo_root

_ACTION_ICONS = {"copied": "+", "COW": "~", "symlinked": "->", "ignored": "x"}
_ACTION_COLORS = {"symlinked": "cyan", "COW": "magenta", "ignored": "dim"}


@command("new", "add")
def _(
    branch: Annotated[
        str, Arg(description="Branch name to check out (or create with --from)")
    ],
    from_ref: Annotated[
        str, Option(name="from", description="Create branch from this ref")
    ] = "",
    worktree_dir: WithConfig[str] = ".worktrees",
    dry_run: Annotated[
        bool, Option(description="Show what would be done without making any changes")
    ] = False,
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
            rich.print(
                f"[bold red]Error:[/bold red] Worktree already exists at [bold]{wt_path}[/bold]"
            )
            failed = True
            continue

        if branch_exists(b):
            if from_ref:
                rich.print(
                    f"[bold red]Error:[/bold red] Branch [bold]{b}[/bold] already exists, cannot create from [bold]{from_ref}[/bold]. Remove --from or delete the branch first."
                )
                failed = True
                continue
            rich.print(
                f"[bold yellow]Warning:[/bold yellow] Branch [bold]{b}[/bold] already exists, checking it out as a worktree"
            )

        if dry_run:
            rich.print(
                f"[bold yellow]dry-run:[/bold yellow] Would create worktree [bold]{b}[/bold] @ [dim]{wt_path}[/dim]"
            )
            share_rules = config.share_rules if config else None
            for entry in get_ignored_entries(repo):
                name = entry.name
                if share_rules is not None:
                    rule = _match_rule(name, share_rules)
                    if rule is None:
                        continue
                    strategy = rule.strategy
                else:
                    strategy = _default_strategy(entry, repo)
                action = "COW" if strategy == "reflink" else strategy
                icon = _ACTION_ICONS.get(action, "+")
                rich.print(
                    f"  [dim]{icon} {entry.relative_to(repo)} ({strategy})[/dim]"
                )
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
                progress.update(
                    task,
                    completed=completed,
                    total=total,
                    current_file=f"{icon} {name}",
                )

            results = copy_ignored_files(
                repo, wt_path, share_rules=share_rules, on_progress=on_progress
            )

        # Run post_create hooks
        if config and config.post_create:
            for cmd in config.post_create:
                rich.print(f"[dim]Running:[/dim] {cmd}")
                result = subprocess.run(cmd, shell=True, cwd=wt_path)
                if result.returncode != 0:
                    rich.print(
                        f"[bold yellow]Warning:[/bold yellow] Command exited with code {result.returncode}"
                    )

        # Print summary
        copied = [r for r in results if r["action"] != "ignored"]
        rich.print(
            f"[bold green]Created worktree[/bold green] [bold]{b}[/bold] @ [dim]{wt_path}[/dim]"
        )
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
                    rich.print(
                        f"  [{color}]{icon}[/{color}] {name} [dim]({action})[/dim]"
                    )

        # Print hint if node_modules was skipped and no post_create hook ran install
        if should_skip_node_modules(repo):
            has_install_hook = config and any(
                "install" in cmd for cmd in config.post_create
            )
            if not has_install_hook:
                install_cmd = detect_package_manager(repo)
                if install_cmd:
                    rich.print(
                        f"[dim]Run[/dim] [bold]{install_cmd}[/bold] [dim]in the worktree to set up dependencies[/dim]"
                    )

    if not dry_run and len(all_branches) == 1 and not failed:
        wt_path = repo / worktree_dir / all_branches[0]
        rich.print(f"[dim]Go to your new worktree with[/dim] [bold]cd {wt_path}[/bold]")

    if failed:
        return 1
