import subprocess

from git_worm.worktree import add_worktree, remove_worktree, list_worktrees, is_dirty, is_merged, get_default_branch


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


def test_get_default_branch_no_remote(git_repo):
    # No remote configured — should fall back to "HEAD"
    assert get_default_branch(cwd=git_repo) == "HEAD"


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
