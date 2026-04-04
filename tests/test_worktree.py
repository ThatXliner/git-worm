import subprocess

from git_werk.worktree import add_worktree, remove_worktree, list_worktrees, is_dirty


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
