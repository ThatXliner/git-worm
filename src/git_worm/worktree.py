"""Thin wrapper around git worktree commands."""

from __future__ import annotations

import subprocess
from pathlib import Path


def add_worktree(path: Path, branch: str, *, from_ref: str | None = None) -> None:
    """Create a new worktree. Creates a new branch if from_ref is given."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if from_ref is not None:
        subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(path), from_ref],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(path), "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )


def remove_worktree(path: Path, *, force: bool = False) -> None:
    """Remove a worktree."""
    cmd = ["git", "worktree", "remove", str(path)]
    if force:
        cmd.append("--force")
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def list_worktrees() -> list[dict[str, str]]:
    """List all worktrees. Returns list of dicts with 'path', 'head', 'branch' keys."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    worktrees = []
    current: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.removeprefix("worktree ")}
        elif line.startswith("HEAD "):
            current["head"] = line.removeprefix("HEAD ")
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch ").removeprefix("refs/heads/")
        elif line == "bare":
            current["bare"] = "true"
        elif line == "detached":
            current["detached"] = "true"
    if current:
        worktrees.append(current)
    return worktrees


def find_repo_root() -> Path:
    """Find the git repo root from cwd."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def is_merged(branch: str) -> bool:
    """Check if a branch has been merged into the main branch (not itself)."""
    result = subprocess.run(
        ["git", "branch", "--merged", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    # Exclude the current branch (prefixed with '*') — it's not "merged", it IS HEAD
    merged = {
        line.strip().lstrip("* ")
        for line in result.stdout.splitlines()
        if not line.startswith("*")
    }
    return branch in merged


def is_dirty(path: Path) -> bool:
    """Check if a worktree has uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())
