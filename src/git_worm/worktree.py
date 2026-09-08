"""Thin wrapper around git worktree commands."""

from __future__ import annotations

from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


def branch_exists(branch: str) -> bool:
    """Return True if a local branch with this name already exists."""
    with Repo(Path.cwd(), search_parent_directories=True) as repo:
        return any(head.name == branch for head in repo.heads)


def add_worktree(path: Path, branch: str, *, from_ref: str | None = None) -> bool:
    """Create a new worktree.

    If the branch already exists, checks it out directly (caller must validate from_ref is not set).
    Otherwise creates a new branch from from_ref (or HEAD if not given).

    Returns True if the branch already existed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if branch_exists(branch):
        with Repo(Path.cwd(), search_parent_directories=True) as repo:
            repo.git.worktree("add", str(path), branch)
        return True
    with Repo(Path.cwd(), search_parent_directories=True) as repo:
        repo.git.worktree("add", "-b", branch, str(path), from_ref or "HEAD")
    return False


def remove_worktree(path: Path, *, force: bool = False) -> None:
    """Remove a worktree."""
    args = ["remove", str(path)]
    if force:
        args.append("--force")
    with Repo(Path.cwd(), search_parent_directories=True) as repo:
        repo.git.worktree(*args)


def find_worktree(branch: str, *, cwd: Path | None = None) -> dict[str, str] | None:
    """Find a worktree by branch name."""
    for wt in list_worktrees(cwd=cwd):
        if wt.get("branch") == branch:
            return wt
    return None


def list_worktrees(cwd: Path | None = None) -> list[dict[str, str]]:
    """List all worktrees. Returns list of dicts with 'path', 'head', 'branch' keys."""
    with Repo(Path.cwd() if cwd is None else cwd, search_parent_directories=True) as repo:
        output = repo.git.worktree("list", "--porcelain", "-z")
    worktrees = []
    current: dict[str, str] = {}
    for field in output.split("\0"):
        if not field:
            continue
        if field.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": str(Path(field.removeprefix("worktree ")))}
        elif field.startswith("HEAD "):
            current["head"] = field.removeprefix("HEAD ")
        elif field.startswith("branch "):
            current["branch"] = field.removeprefix("branch ").removeprefix("refs/heads/")
        elif field == "bare":
            current["bare"] = "true"
        elif field == "detached":
            current["detached"] = "true"
    if current:
        worktrees.append(current)
    return worktrees


def find_repo_root() -> Path:
    """Find the git repo root from cwd."""
    with Repo(Path.cwd(), search_parent_directories=True) as repo:
        if repo.bare or repo.working_tree_dir is None:
            raise InvalidGitRepositoryError("Cannot find a working tree for a bare repository")
        return Path(repo.working_tree_dir)


def get_default_branch(cwd: Path | None = None) -> str:
    """Return the default branch name.

    Tries in order:
    1. refs/remotes/origin/HEAD (remote's default branch)
    2. Primary worktree's branch (local default when no remote)
    """
    repo_path = Path.cwd() if cwd is None else cwd
    try:
        with Repo(repo_path, search_parent_directories=True) as repo:
            remote_head = repo.git.symbolic_ref("refs/remotes/origin/HEAD")
    except GitCommandError:
        remote_head = None
    if remote_head is not None:
        return remote_head.strip().removeprefix("refs/remotes/origin/")
    worktrees = list_worktrees(cwd=cwd)
    if worktrees and "branch" in worktrees[0]:
        return worktrees[0]["branch"]
    return "HEAD"


def is_merged(branch: str, cwd: Path | None = None) -> bool:
    """Check if a branch has been merged into the default branch."""
    default = get_default_branch(cwd=cwd)
    if branch == default:
        return False
    with Repo(Path.cwd() if cwd is None else cwd, search_parent_directories=True) as repo:
        try:
            return repo.is_ancestor(branch, default)
        except GitCommandError:
            return False


def is_dirty(path: Path) -> bool:
    """Check if a worktree has uncommitted changes."""
    with Repo(path, search_parent_directories=True) as repo:
        return repo.is_dirty(untracked_files=True)


def prune_worktrees(cwd: Path | None = None, *, dry_run: bool = False) -> list[str]:
    """Prune stale worktree references and return verbose output lines."""
    args = ["prune"]
    if dry_run:
        args.append("--dry-run")
    args.extend(["--verbose", "--expire=now"])
    with Repo(Path.cwd() if cwd is None else cwd, search_parent_directories=True) as repo:
        _, stdout, stderr = repo.git.worktree(*args, with_extended_output=True)
    output = "\n".join(part for part in (stderr, stdout) if part)
    return output.strip().splitlines() if output.strip() else []
