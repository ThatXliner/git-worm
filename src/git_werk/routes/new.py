from pathlib import Path

import rich

from git_werk.config import load_config
from git_werk.files import copy_ignored_files
from git_werk.worktree import add_worktree
from xclif import command


@command()
def _(branch: str, from_ref: str = "") -> None:
    """Create a new worktree for a branch.

    BRANCH is the branch name to check out (or create with --from-ref).
    """
    repo = _find_repo_root()
    config = load_config(repo / ".git-werk.toml")
    worktree_dir = config.worktree_dir if config else ".worktrees"
    wt_path = repo / worktree_dir / branch

    if wt_path.exists():
        rich.print(f"[bold red]Error:[/bold red] Worktree already exists at [bold]{wt_path}[/bold]")
        return

    # Create the worktree
    add_worktree(wt_path, branch, from_ref=from_ref or None)

    # Ensure .worktrees/.gitignore exists
    wt_dir = repo / worktree_dir
    gitignore = wt_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n")

    # Copy gitignored files
    share_rules = config.share_rules if config else None
    results = copy_ignored_files(repo, wt_path, share_rules=share_rules)

    # Print summary
    rich.print(f"\n[bold green]Created worktree[/bold green] [bold]{branch}[/bold] @ [dim]{wt_path}[/dim]")
    if results:
        rich.print("[dim]Copied files:[/dim]")
        for r in results:
            icon = {"copied": "+", "reflinked": "~", "symlinked": "->", "ignored": "x"}.get(
                r["action"], "?"
            )
            if r["action"] == "ignored":
                rich.print(f"  [dim]{icon} {r['name']} ({r['action']})[/dim]")
            else:
                rich.print(f"  {icon} {r['name']} ({r['action']})")


def _find_repo_root() -> Path:
    """Find the git repo root from cwd."""
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())
