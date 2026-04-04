from pathlib import Path

from git_werk.config import load_config, Config, ShareRule


def test_load_config_no_file(tmp_path):
    config = load_config(tmp_path / "nonexistent.toml")
    assert config is None


def test_load_config_basic(tmp_path):
    toml_file = tmp_path / ".git-werk.toml"
    toml_file.write_text("""\
[settings]
worktree_dir = "wt"

[[share]]
path = ".env*"
strategy = "copy"

[[share]]
path = "node_modules"
strategy = "ignore"
""")
    config = load_config(toml_file)
    assert config is not None
    assert config.worktree_dir == "wt"
    assert len(config.share_rules) == 2
    assert config.share_rules[0] == ShareRule(path=".env*", strategy="copy")
    assert config.share_rules[1] == ShareRule(path="node_modules", strategy="ignore")


def test_load_config_defaults(tmp_path):
    toml_file = tmp_path / ".git-werk.toml"
    toml_file.write_text("""\
[[share]]
path = "target"
strategy = "symlink"
""")
    config = load_config(toml_file)
    assert config is not None
    assert config.worktree_dir == ".worktrees"
    assert len(config.share_rules) == 1


def test_load_config_empty_settings(tmp_path):
    toml_file = tmp_path / ".git-werk.toml"
    toml_file.write_text("""\
[settings]
""")
    config = load_config(toml_file)
    assert config is not None
    assert config.worktree_dir == ".worktrees"
    assert config.share_rules == []
