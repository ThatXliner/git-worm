"""Parse .git-worm.toml configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ShareRule:
    path: str
    strategy: str  # "copy", "reflink", "symlink", "ignore"


@dataclass
class Config:
    worktree_dir: str = ".worktrees"
    share_rules: list[ShareRule] = field(default_factory=list)


def load_config(path: Path) -> Config | None:
    """Load config from a TOML file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = tomllib.load(f)
    share_rules = [
        ShareRule(path=rule["path"], strategy=rule["strategy"])
        for rule in data.get("share", [])
    ]
    return Config(
        worktree_dir=data.get("worktree_dir", ".worktrees"),
        share_rules=share_rules,
    )
