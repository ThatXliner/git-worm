"""Integration tests that run git-worm as a subprocess, like a real user would."""

import os
import subprocess
import textwrap

import pytest


def _run(args: list[str], cwd, *, check=True):
    """Run git-worm as a subprocess."""
    return subprocess.run(
        ["git-worm", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def _git(args: list[str], cwd, *, check=True):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


@pytest.fixture()
def repo(tmp_path):
    """Create a temporary git repo with an initial commit."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(["init"], r)
    _git(["config", "user.email", "test@test.com"], r)
    _git(["config", "user.name", "Test"], r)
    (r / "README.md").write_text("hello")
    _git(["add", "."], r)
    _git(["commit", "-m", "init"], r)
    old = os.getcwd()
    os.chdir(r)
    yield r
    os.chdir(old)


class TestNew:
    def test_basic(self, repo):
        result = _run(["new", "feat-basic"], repo)
        assert result.returncode == 0
        wt = repo / ".worktrees" / "feat-basic"
        assert wt.exists()
        assert (wt / "README.md").exists()

    def test_copies_gitignored_file(self, repo):
        (repo / ".gitignore").write_text(".env\n")
        _git(["add", ".gitignore"], repo)
        _git(["commit", "-m", "add gitignore"], repo)
        (repo / ".env").write_text("SECRET=42")

        result = _run(["new", "feat-env"], repo)
        assert result.returncode == 0
        assert (repo / ".worktrees" / "feat-env" / ".env").read_text() == "SECRET=42"

    def test_copies_gitignored_directory(self, repo):
        (repo / ".gitignore").write_text(".venv/\n")
        _git(["add", ".gitignore"], repo)
        _git(["commit", "-m", "add gitignore"], repo)
        venv = repo / ".venv" / "bin"
        venv.mkdir(parents=True)
        (venv / "python").write_text("#!/usr/bin/env python")

        result = _run(["new", "feat-venv"], repo)
        assert result.returncode == 0
        assert (repo / ".worktrees" / "feat-venv" / ".venv" / "bin" / "python").exists()

    def test_tracked_dir_with_ignored_file_inside(self, repo):
        """Regression: a tracked dir containing an ignored file should not
        cause a FileExistsError from copytree trying to overwrite the
        tracked directory."""
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("print('hi')")
        (repo / ".gitignore").write_text("*.pyc\n")
        _git(["add", "."], repo)
        _git(["commit", "-m", "add src and gitignore"], repo)
        (repo / "src" / "foo.pyc").write_text("cache")

        result = _run(["new", "feat-pyc"], repo)
        assert result.returncode == 0
        wt = repo / ".worktrees" / "feat-pyc"
        # The tracked file must exist
        assert (wt / "src" / "main.py").exists()
        # The ignored file should be copied in
        assert (wt / "src" / "foo.pyc").exists()

    def test_from_ref(self, repo):
        _git(["commit", "--allow-empty", "-m", "second"], repo)
        result = _run(["new", "feat-from", "--from", "HEAD~1"], repo)
        assert result.returncode == 0
        assert (repo / ".worktrees" / "feat-from").exists()

    def test_duplicate_worktree_fails(self, repo):
        _run(["new", "feat-dup"], repo)
        result = _run(["new", "feat-dup"], repo, check=False)
        assert "Error" in result.stdout or result.returncode != 0


class TestRm:
    def test_basic(self, repo):
        _run(["new", "feat-rm"], repo)
        assert (repo / ".worktrees" / "feat-rm").exists()

        result = _run(["rm", "feat-rm"], repo)
        assert result.returncode == 0
        assert not (repo / ".worktrees" / "feat-rm").exists()

    def test_dirty_without_force(self, repo):
        _run(["new", "feat-dirty"], repo)
        (repo / ".worktrees" / "feat-dirty" / "untracked.txt").write_text("dirty")

        result = _run(["rm", "feat-dirty"], repo, check=False)
        assert result.returncode != 0

    def test_dirty_with_force(self, repo):
        _run(["new", "feat-force"], repo)
        (repo / ".worktrees" / "feat-force" / "untracked.txt").write_text("dirty")

        result = _run(["rm", "feat-force", "--force"], repo)
        assert result.returncode == 0

    def test_nonexistent(self, repo):
        result = _run(["rm", "nonexistent"], repo, check=False)
        assert result.returncode != 0


class TestList:
    def test_shows_worktrees(self, repo):
        _run(["new", "feat-list"], repo)
        result = _run(["list"], repo)
        assert result.returncode == 0
        assert "feat-list" in result.stdout

    def test_empty(self, repo):
        result = _run(["list"], repo)
        assert result.returncode == 0


class TestSwitch:
    def test_prints_path(self, repo):
        _run(["new", "feat-sw"], repo)
        result = _run(["switch", "feat-sw"], repo)
        assert result.returncode == 0
        # Rich may wrap long paths with newlines; collapse them
        stdout = result.stdout.replace("\n", "")
        assert str(repo / ".worktrees" / "feat-sw") in stdout

    def test_nonexistent(self, repo):
        result = _run(["switch", "nonexistent"], repo, check=False)
        assert result.returncode != 0


class TestShellInit:
    def test_outputs_function(self, repo):
        result = _run(["shell-init"], repo)
        assert result.returncode == 0
        assert "worm()" in result.stdout or "worm ()" in result.stdout
        assert "cd" in result.stdout


class TestEndToEnd:
    def test_full_workflow(self, repo):
        """new -> list -> switch -> rm"""
        (repo / ".gitignore").write_text(".env\n")
        _git(["add", ".gitignore"], repo)
        _git(["commit", "-m", "gitignore"], repo)
        (repo / ".env").write_text("DB_URL=localhost")

        assert _run(["new", "feat-e2e"], repo).returncode == 0
        assert (repo / ".worktrees" / "feat-e2e" / ".env").read_text() == "DB_URL=localhost"

        r = _run(["list"], repo)
        assert "feat-e2e" in r.stdout

        r = _run(["switch", "feat-e2e"], repo)
        assert str(repo / ".worktrees" / "feat-e2e") in r.stdout.replace("\n", "")

        assert _run(["rm", "feat-e2e"], repo).returncode == 0
        assert not (repo / ".worktrees" / "feat-e2e").exists()
