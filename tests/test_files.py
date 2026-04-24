import subprocess
from pathlib import Path

from git_worm.files import get_ignored_entries, copy_entry, should_skip_node_modules, copy_ignored_files
from git_worm.config import ShareRule


def test_get_ignored_entries(git_repo):
    (git_repo / ".gitignore").write_text(".env\nbuild/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (git_repo / ".env").write_text("SECRET=foo")
    (git_repo / "build").mkdir()
    (git_repo / "build" / "out.js").write_text("x")

    entries = get_ignored_entries(git_repo)
    names = [e.name for e in entries]
    assert ".env" in names
    assert "build" in names


def test_get_ignored_entries_excludes_git_and_worktrees(git_repo):
    (git_repo / ".gitignore").write_text(".worktrees/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (git_repo / ".worktrees").mkdir()
    (git_repo / ".worktrees" / "x").write_text("y")

    entries = get_ignored_entries(git_repo)
    names = [e.name for e in entries]
    assert ".worktrees" not in names
    assert ".git" not in names


def test_copy_entry_file(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / ".env").write_text("KEY=val")
    dst = tmp_path / "dst"
    dst.mkdir()

    copy_entry(src / ".env", src, dst, strategy="copy")
    assert (dst / ".env").read_text() == "KEY=val"


def test_copy_entry_directory_reflink(tmp_path):
    src = tmp_path / "src"
    (src / "node_modules" / "pkg").mkdir(parents=True)
    (src / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1")
    dst = tmp_path / "dst"
    dst.mkdir()

    copy_entry(src / "node_modules", src, dst, strategy="reflink")
    assert (dst / "node_modules" / "pkg" / "index.js").read_text() == "module.exports = 1"


def test_copy_entry_symlink(tmp_path):
    src = tmp_path / "src"
    (src / "target").mkdir(parents=True)
    (src / "target" / "debug").mkdir()
    dst = tmp_path / "dst"
    dst.mkdir()

    copy_entry(src / "target", src, dst, strategy="symlink")
    assert (dst / "target").is_symlink()
    assert (dst / "target").resolve() == (src / "target").resolve()


def test_copy_entry_ignore(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "ignored").write_text("x")
    dst = tmp_path / "dst"
    dst.mkdir()

    copy_entry(src / "ignored", src, dst, strategy="ignore")
    assert not (dst / "ignored").exists()


def test_should_skip_node_modules_pnpm(git_repo):
    (git_repo / "pnpm-lock.yaml").write_text("")
    assert should_skip_node_modules(git_repo) is True


def test_should_skip_node_modules_bun(git_repo):
    (git_repo / "bun.lockb").write_text("")
    assert should_skip_node_modules(git_repo) is True


def test_should_skip_node_modules_bun_text_lock(git_repo):
    (git_repo / "bun.lock").write_text("")
    assert should_skip_node_modules(git_repo) is True


def test_should_skip_node_modules_yarn_pnp(git_repo):
    (git_repo / "yarn.lock").write_text("")
    (git_repo / ".pnp.cjs").write_text("")
    assert should_skip_node_modules(git_repo) is True


def test_should_skip_node_modules_yarn_pnp_mjs(git_repo):
    (git_repo / "yarn.lock").write_text("")
    (git_repo / ".pnp.mjs").write_text("")
    assert should_skip_node_modules(git_repo) is True


def test_should_skip_node_modules_deno(git_repo):
    (git_repo / "deno.lock").write_text("{}")
    assert should_skip_node_modules(git_repo) is True


def test_should_skip_node_modules_npm(git_repo):
    (git_repo / "package-lock.json").write_text("{}")
    assert should_skip_node_modules(git_repo) is False


def test_should_skip_node_modules_no_lockfile(git_repo):
    assert should_skip_node_modules(git_repo) is False


def test_copy_ignored_files_with_config(git_repo):
    (git_repo / ".gitignore").write_text(".env\nbuild/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (git_repo / ".env").write_text("SECRET=1")
    (git_repo / "build").mkdir()
    (git_repo / "build" / "out.js").write_text("x")

    dst = git_repo / ".worktrees" / "test-branch"
    dst.mkdir(parents=True)

    rules = [
        ShareRule(path=".env", strategy="copy"),
        ShareRule(path="build", strategy="ignore"),
    ]
    results = copy_ignored_files(git_repo, dst, share_rules=rules)
    assert (dst / ".env").exists()
    assert not (dst / "build").exists()
    assert any(r["action"] == "copied" for r in results)
    assert any(r["action"] == "ignored" for r in results)


def test_copy_ignored_files_matches_relative_paths(git_repo):
    (git_repo / "src").mkdir()
    (git_repo / "src" / "main.py").write_text("print('hi')")
    (git_repo / ".gitignore").write_text("*.pyc\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (git_repo / "src" / "cache.pyc").write_text("cache")

    dst = git_repo / ".worktrees" / "test-branch"
    dst.mkdir(parents=True)

    results = copy_ignored_files(
        git_repo,
        dst,
        share_rules=[ShareRule(path="src/*.pyc", strategy="copy")],
    )
    assert (dst / "src" / "cache.pyc").read_text() == "cache"
    assert results == [{"name": "src/cache.pyc", "action": "copied"}]
