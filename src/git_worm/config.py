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
    post_create: list[str] = field(default_factory=list)


def load_config(path: Path) -> Config | None:
    """Load config from a TOML file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = tomllib.load(f)
    settings = data.get("settings", {})
    raw_share_rules = data.get("share", [])
    share_rules = [
        ShareRule(path=rule["path"], strategy=rule["strategy"])
        for rule in raw_share_rules
    ]
    post_create = data.get("post_create", settings.get("post_create", []))
    if not post_create:
        for rule in raw_share_rules:
            if "post_create" in rule:
                post_create = rule["post_create"]
                break
    return Config(
        worktree_dir=data.get("worktree_dir", settings.get("worktree_dir", ".worktrees")),
        share_rules=share_rules,
        post_create=post_create,
    )
