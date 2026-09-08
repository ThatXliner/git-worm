import shutil
import subprocess

import pytest
from git.exc import GitCommandError, InvalidGitRepositoryError

from git_worm.worktree import (
    add_worktree,
    branch_exists,
    find_repo_root,
    get_default_branch,
    is_dirty,
    is_merged,
    list_worktrees,
    prune_worktrees,
    remove_worktree,
)


def test_add_worktree_creates_directory(git_repo):
    wt_path = git_repo / ".worktrees" / "feat"
    add_worktree(wt_path, "feat")
    assert wt_path.exists()
    assert (wt_path / "README.md").exists()


def test_add_worktree_from_ref(git_repo):
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "second"],
        cwd=git_repo, check=True, capture_output=True,
    )
    wt_path = git_repo / ".worktrees" / "from-head"
    add_worktree(wt_path, "from-head", from_ref="HEAD~1")
    assert wt_path.exists()


def test_list_worktrees_includes_new(git_repo):
    wt_path = git_repo / ".worktrees" / "listed"
    add_worktree(wt_path, "listed")
    worktrees = list_worktrees()
    paths = [w["path"] for w in worktrees]
    assert str(wt_path) in paths


def test_remove_worktree(git_repo):
    wt_path = git_repo / ".worktrees" / "removable"
    add_worktree(wt_path, "removable")
    remove_worktree(wt_path)
    assert not wt_path.exists()


def test_is_dirty_clean_repo(git_repo):
    assert not is_dirty(git_repo)


def test_is_dirty_with_changes(git_repo):
    (git_repo / "new_file.txt").write_text("dirty")
    assert is_dirty(git_repo)


def test_is_dirty_with_tracked_changes(git_repo):
    (git_repo / "README.md").write_text("dirty")
    assert is_dirty(git_repo)


def test_is_dirty_with_staged_changes_and_ignores_ignored_files(git_repo):
    (git_repo / ".gitignore").write_text("ignored.txt\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add gitignore"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    (git_repo / "ignored.txt").write_text("ignored")
    assert not is_dirty(git_repo)

    (git_repo / "README.md").write_text("staged")
    subprocess.run(["git", "add", "README.md"], cwd=git_repo, check=True, capture_output=True)
    assert is_dirty(git_repo)


def test_branch_exists_only_checks_local_branches(git_repo):
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "tag", "v1"], cwd=git_repo, check=True, capture_output=True)

    assert branch_exists(branch)
    assert not branch_exists("v1")


def test_find_repo_root_from_nested_directory(git_repo, monkeypatch):
    nested = git_repo / "nested" / "directory"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    assert find_repo_root() == git_repo


def test_find_repo_root_rejects_bare_repo(tmp_path, monkeypatch):
    bare = tmp_path / "bare.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    monkeypatch.chdir(bare)

    with pytest.raises(InvalidGitRepositoryError):
        find_repo_root()


def test_list_worktrees_marks_detached_worktree(git_repo):
    wt_path = git_repo / ".worktrees" / "detached"
    add_worktree(wt_path, "detached")
    subprocess.run(
        ["git", "checkout", "--detach", "HEAD"],
        cwd=wt_path,
        check=True,
        capture_output=True,
    )

    worktree = next(wt for wt in list_worktrees() if wt["path"] == str(wt_path))
    assert worktree.get("detached") == "true"
    assert "branch" not in worktree


def test_remove_dirty_worktree_requires_force(git_repo):
    wt_path = git_repo / ".worktrees" / "dirty"
    add_worktree(wt_path, "dirty")
    (wt_path / "untracked.txt").write_text("dirty")

    with pytest.raises(GitCommandError):
        remove_worktree(wt_path)

    remove_worktree(wt_path, force=True)
    assert not wt_path.exists()


def test_prune_worktrees_dry_run_then_removes_stale_ref(git_repo):
    wt_path = git_repo / ".worktrees" / "stale"
    add_worktree(wt_path, "stale")
    shutil.rmtree(wt_path)

    dry_run_lines = prune_worktrees(cwd=git_repo, dry_run=True)
    assert dry_run_lines
    assert any("stale" in line for line in dry_run_lines)
    assert any(wt.get("branch") == "stale" for wt in list_worktrees(cwd=git_repo))

    prune_worktrees(cwd=git_repo)
    assert all(wt.get("branch") != "stale" for wt in list_worktrees(cwd=git_repo))


def test_get_default_branch_no_remote(git_repo):
    # No remote configured — should fall back to the primary worktree's branch
    branch = get_default_branch(cwd=git_repo)
    assert branch != "HEAD"
    assert branch  # non-empty branch name


def test_get_default_branch_no_remote_uses_cwd(git_repo, tmp_path, monkeypatch):
    """Fallback worktree lookup should use the requested repo, not process cwd."""
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "--initial-branch=other-main"], cwd=other, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=other, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=other, check=True, capture_output=True)
    (other / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=other, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=other, check=True, capture_output=True)

    monkeypatch.chdir(other)

    assert get_default_branch(cwd=git_repo) != "other-main"


def test_get_default_branch_with_remote(tmp_path):
    """get_default_branch returns the remote's default branch when origin/HEAD is set."""
    # Set up a "remote" repo
    remote = tmp_path / "remote"
    remote.mkdir()
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=remote, check=True, capture_output=True)
    (remote / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=remote, check=True, capture_output=True)

    # Clone it so origin/HEAD gets set
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(remote), str(clone)], check=True, capture_output=True)

    assert get_default_branch(cwd=clone) == "main"


def test_is_merged_against_default_branch(tmp_path):
    """is_merged checks against origin/HEAD (default branch), not current HEAD."""
    # Set up remote with main branch
    remote = tmp_path / "remote"
    remote.mkdir()
    subprocess.run(["git", "init", "--initial-branch=main"], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=remote, check=True, capture_output=True)
    (remote / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=remote, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=remote, check=True, capture_output=True)

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(remote), str(clone)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=clone, check=True, capture_output=True)

    # Create a branch, merge it into main, push
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=clone, check=True, capture_output=True)
    (clone / "g.txt").write_text("y")
    subprocess.run(["git", "add", "."], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feature commit"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "main"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "merge", "feature", "--no-ff", "-m", "merge feature"], cwd=clone, check=True, capture_output=True)

    assert is_merged("feature", cwd=clone)


def test_is_merged_unmerged_branch(git_repo):
    subprocess.run(["git", "checkout", "-b", "unmerged"], cwd=git_repo, check=True, capture_output=True)
    # Add a commit so this branch diverges from the default branch
    subprocess.run(["git", "commit", "--allow-empty", "-m", "unmerged commit"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-"], cwd=git_repo, check=True, capture_output=True)
    # Did not merge
    assert not is_merged("unmerged", cwd=git_repo)


def test_is_merged_uses_cwd_for_default_branch(git_repo, tmp_path, monkeypatch):
    """is_merged should compare against the target repo's default branch."""
    subprocess.run(["git", "checkout", "-b", "merged"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "merged commit"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(["git", "merge", "merged"], cwd=git_repo, check=True, capture_output=True)

    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "--initial-branch=other-main"], cwd=other, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=other, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=other, check=True, capture_output=True)
    (other / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=other, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=other, check=True, capture_output=True)
    monkeypatch.chdir(other)

    assert is_merged("merged", cwd=git_repo)
