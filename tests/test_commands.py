import subprocess
from dataclasses import replace

from git_worm import routes
from xclif import Cli


def _make_cli():
    # Reset shared root command state to avoid cross-test alias collisions
    routes._.subcommands.clear()
    routes._.implicit_options.clear()
    return Cli.from_routes(routes)


def test_new_creates_worktree(git_repo, capsys):
    cli = _make_cli()
    result = cli.root_command.execute(["new", "feat-test"])
    assert result == 0
    wt = git_repo / ".worktrees" / "feat-test"
    assert wt.exists()
    assert (wt / "README.md").exists()
    out = capsys.readouterr().out
    assert "feat-test" in out


def test_new_copies_gitignored_files(git_repo, capsys):
    (git_repo / ".gitignore").write_text(".env\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "gitignore"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (git_repo / ".env").write_text("SECRET=42")

    cli = _make_cli()
    result = cli.root_command.execute(["new", "feat-env"])
    assert result == 0
    assert (git_repo / ".worktrees" / "feat-env" / ".env").read_text() == "SECRET=42"


def test_new_creates_worktree_gitignore(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-ign"])
    gitignore = git_repo / ".worktrees" / ".gitignore"
    assert gitignore.exists()
    assert "*" in gitignore.read_text()


def test_new_with_from_ref(git_repo, capsys):
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "second"],
        cwd=git_repo, check=True, capture_output=True,
    )
    cli = _make_cli()
    result = cli.root_command.execute(["new", "feat-from", "--from", "HEAD~1"])
    assert result == 0
    assert (git_repo / ".worktrees" / "feat-from").exists()


def test_rm_removes_worktree(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-rm"])
    assert (git_repo / ".worktrees" / "feat-rm").exists()

    result = cli.root_command.execute(["rm", "feat-rm"])
    assert result == 0
    assert not (git_repo / ".worktrees" / "feat-rm").exists()


def test_rm_dirty_worktree_without_force(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-dirty"])
    (git_repo / ".worktrees" / "feat-dirty" / "untracked.txt").write_text("dirty")

    result = cli.root_command.execute(["rm", "feat-dirty"])
    assert result != 0


def test_rm_dirty_worktree_with_force(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-force"])
    (git_repo / ".worktrees" / "feat-force" / "untracked.txt").write_text("dirty")

    result = cli.root_command.execute(["rm", "feat-force", "--force"])
    assert result == 0


def test_rm_nonexistent_worktree(git_repo, capsys):
    cli = _make_cli()
    result = cli.root_command.execute(["rm", "nonexistent"])
    assert result != 0


def test_list_shows_worktrees(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-list"])

    result = cli.root_command.execute(["list"])
    assert result == 0
    out = capsys.readouterr().out
    assert "feat-list" in out


def test_list_empty(git_repo, capsys):
    cli = _make_cli()
    result = cli.root_command.execute(["list"])
    assert result == 0


def test_switch_prints_path(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-switch"])

    result = cli.root_command.execute(["switch", "feat-switch"])
    assert result == 0
    out = capsys.readouterr().out
    assert str(git_repo / ".worktrees" / "feat-switch") in out.replace("\n", "")


def test_switch_nonexistent(git_repo, capsys):
    cli = _make_cli()
    result = cli.root_command.execute(["switch", "nonexistent"])
    assert result != 0


def test_shell_init_outputs_function(git_repo, capsys):
    cli = _make_cli()
    result = cli.root_command.execute(["shell-init"])
    assert result == 0
    out = capsys.readouterr().out
    assert "worm()" in out or "worm ()" in out
    assert "cd" in out
    assert "git-worm" in out


def test_full_workflow(git_repo, capsys):
    """End-to-end: new -> list -> switch -> rm."""
    (git_repo / ".gitignore").write_text(".env\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "gitignore"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (git_repo / ".env").write_text("DB_URL=localhost")

    cli = _make_cli()

    # new
    assert cli.root_command.execute(["new", "feat-e2e"]) == 0
    assert (git_repo / ".worktrees" / "feat-e2e" / ".env").read_text() == "DB_URL=localhost"
    capsys.readouterr()

    # list
    assert cli.root_command.execute(["list"]) == 0
    assert "feat-e2e" in capsys.readouterr().out

    # switch
    assert cli.root_command.execute(["switch", "feat-e2e"]) == 0
    out = capsys.readouterr().out.replace("\n", "")
    assert str(git_repo / ".worktrees" / "feat-e2e") in out

    # rm
    assert cli.root_command.execute(["rm", "feat-e2e"]) == 0
    assert not (git_repo / ".worktrees" / "feat-e2e").exists()


def test_prune_merged_removes_merged_worktrees(git_repo, capsys):
    """Prune --merged removes worktrees whose branches are merged into main."""
    cli = _make_cli()

    # Create a worktree, make a commit, then merge it into main
    cli.root_command.execute(["new", "feat-merged"])
    wt_path = git_repo / ".worktrees" / "feat-merged"
    (wt_path / "new_file.txt").write_text("feature work")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat work"],
        cwd=wt_path, check=True, capture_output=True,
    )
    # Merge feat-merged into main
    subprocess.run(
        ["git", "merge", "feat-merged"],
        cwd=git_repo, check=True, capture_output=True,
    )

    assert wt_path.exists()
    result = cli.root_command.execute(["prune", "--merged", "--yes"])
    assert result == 0
    assert not wt_path.exists()
    out = capsys.readouterr().out
    assert "feat-merged" in out


def test_prune_merged_keeps_unmerged_worktrees(git_repo, capsys):
    """Prune --merged does not remove worktrees with unmerged commits."""
    cli = _make_cli()

    cli.root_command.execute(["new", "feat-unmerged"])
    wt_path = git_repo / ".worktrees" / "feat-unmerged"
    (wt_path / "new_file.txt").write_text("unmerged work")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "unmerged work"],
        cwd=wt_path, check=True, capture_output=True,
    )

    assert wt_path.exists()
    result = cli.root_command.execute(["prune", "--merged"])
    assert result == 0
    assert wt_path.exists()
    out = capsys.readouterr().out
    assert "Nothing to prune." in out
