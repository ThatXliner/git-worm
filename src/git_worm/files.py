"""Gitignored file detection and copy/reflink/symlink logic."""

from __future__ import annotations

import shutil
import subprocess
from fnmatch import fnmatch
from pathlib import Path

from git_worm.config import ShareRule

EXCLUDED_NAMES = {".git", ".worktrees"}


def _has_tracked_files(repo: Path, directory: str) -> bool:
    """Check if a directory contains any files tracked by git."""
    result = subprocess.run(
        ["git", "ls-files", directory],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def get_ignored_entries(repo: Path) -> list[Path]:
    """Get gitignored files and directories in the repo.

    Returns top-level entries when the entire directory is ignored.
    For tracked directories that contain ignored files, returns the
    individual ignored file paths instead.
    """
    result = subprocess.run(
        ["git", "status", "--ignored", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    entries = []
    seen: set[str] = set()
    for line in result.stdout.splitlines():
        if not line.startswith("!! "):
            continue
        rel = line.removeprefix("!! ").rstrip("/")
        top_level = rel.split("/")[0]
        if top_level in EXCLUDED_NAMES:
            continue
        path = repo / top_level
        if not path.exists():
            continue
        if top_level in seen:
            continue
        # If this is a directory that also has tracked files, we can't
        # copy the whole thing — get the individual ignored files instead.
        if path.is_dir() and _has_tracked_files(repo, top_level):
            seen.add(top_level)
            nested = _get_ignored_files_in(repo, top_level)
            entries.extend(nested)
        else:
            seen.add(top_level)
            entries.append(path)
    return entries


def _get_ignored_files_in(repo: Path, directory: str) -> list[Path]:
    """Get individual ignored file paths within a partially-tracked directory."""
    result = subprocess.run(
        ["git", "status", "--ignored", "--porcelain", directory],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        if not line.startswith("!! "):
            continue
        rel = line.removeprefix("!! ").rstrip("/")
        path = repo / rel
        if path.exists():
            paths.append(path)
    return paths


def should_skip_node_modules(repo: Path) -> bool:
    """Detect if the package manager handles node_modules efficiently."""
    if (repo / "pnpm-lock.yaml").exists():
        return True
    if (repo / "bun.lockb").exists():
        return True
    if (repo / "yarn.lock").exists() and (repo / ".pnp.cjs").exists():
        return True
    return False


def copy_entry(
    entry: Path,
    src_root: Path,
    dst_root: Path,
    *,
    strategy: str,
) -> dict[str, str]:
    """Copy a single file or directory using the given strategy.

    Returns a dict with 'name' and 'action' keys describing what happened.
    """
    rel = entry.relative_to(src_root)
    dst = dst_root / rel
    name = str(rel)

    if strategy == "ignore":
        return {"name": name, "action": "ignored"}

    if strategy == "symlink":
        dst.symlink_to(entry.resolve())
        return {"name": name, "action": "symlinked"}

    if strategy == "copy":
        if entry.is_dir():
            shutil.copytree(entry, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, dst)
        return {"name": name, "action": "copied"}

    if strategy == "reflink":
        if entry.is_dir():
            # Try cp --reflink=auto, fall back to shutil.copytree
            try:
                subprocess.run(
                    ["cp", "-a", "--reflink=auto", str(entry), str(dst)],
                    check=True,
                    capture_output=True,
                )
                return {"name": name, "action": "reflinked"}
            except (subprocess.CalledProcessError, FileNotFoundError):
                shutil.copytree(entry, dst)
                return {"name": name, "action": "copied (reflink unavailable)"}
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(
                    ["cp", "--reflink=auto", str(entry), str(dst)],
                    check=True,
                    capture_output=True,
                )
                return {"name": name, "action": "reflinked"}
            except (subprocess.CalledProcessError, FileNotFoundError):
                shutil.copy2(entry, dst)
                return {"name": name, "action": "copied (reflink unavailable)"}

    return {"name": name, "action": f"unknown strategy: {strategy}"}


def _default_strategy(entry: Path, repo: Path) -> str:
    """Determine the default strategy for an ignored entry."""
    if entry.name == "node_modules" and should_skip_node_modules(repo):
        return "ignore"
    if entry.is_dir():
        return "reflink"
    return "copy"


def _match_rule(entry_name: str, rules: list[ShareRule]) -> ShareRule | None:
    """Find the first matching share rule for an entry name."""
    for rule in rules:
        if fnmatch(entry_name, rule.path):
            return rule
    return None


def copy_ignored_files(
    src: Path,
    dst: Path,
    *,
    share_rules: list[ShareRule] | None = None,
) -> list[dict[str, str]]:
    """Copy all gitignored files from src to dst.

    If share_rules is provided, it replaces default behavior entirely.
    """
    entries = get_ignored_entries(src)
    results = []

    for entry in entries:
        name = entry.name
        if share_rules is not None:
            rule = _match_rule(name, share_rules)
            if rule is None:
                # Config present but no rule matches -> skip
                continue
            strategy = rule.strategy
        else:
            strategy = _default_strategy(entry, src)

        result = copy_entry(entry, src, dst, strategy=strategy)
        results.append(result)

    return results
