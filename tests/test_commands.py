import subprocess
import shutil
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
    result = cli.root_command.execute(["new", "feat-from", "--from-ref", "HEAD~1"])
    assert result == 0
    assert (git_repo / ".worktrees" / "feat-from").exists()


def test_rm_removes_worktree(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-rm"])
    assert (git_repo / ".worktrees" / "feat-rm").exists()

    result = cli.root_command.execute(["rm", "feat-rm", "--yes"])
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

    result = cli.root_command.execute(["rm", "feat-force", "--force", "--yes"])
    assert result == 0


def test_rm_confirmation_aborts(git_repo, capsys, monkeypatch):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-confirm"])
    assert (git_repo / ".worktrees" / "feat-confirm").exists()

    monkeypatch.setattr("builtins.input", lambda _: "n")
    result = cli.root_command.execute(["rm", "feat-confirm"])
    assert (git_repo / ".worktrees" / "feat-confirm").exists()
    out = capsys.readouterr().out
    assert "Aborted" in out


def test_rm_confirmation_accepts(git_repo, capsys, monkeypatch):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-confirm-yes"])
    assert (git_repo / ".worktrees" / "feat-confirm-yes").exists()

    monkeypatch.setattr("builtins.input", lambda _: "y")
    result = cli.root_command.execute(["rm", "feat-confirm-yes"])
    assert result == 0
    assert not (git_repo / ".worktrees" / "feat-confirm-yes").exists()


def test_rm_dry_run(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-dry"])
    assert (git_repo / ".worktrees" / "feat-dry").exists()

    result = cli.root_command.execute(["rm", "feat-dry", "--dry-run"])
    assert result == 0
    assert (git_repo / ".worktrees" / "feat-dry").exists()
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "feat-dry" in out


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


def test_list_suggests_prune_for_merged(git_repo, capsys):
    """List shows a prune suggestion when merged worktrees exist."""
    cli = _make_cli()

    cli.root_command.execute(["new", "feat-done"])
    wt_path = git_repo / ".worktrees" / "feat-done"
    (wt_path / "new_file.txt").write_text("feature work")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat work"],
        cwd=wt_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feat-done"],
        cwd=git_repo, check=True, capture_output=True,
    )

    result = cli.root_command.execute(["list"])
    assert result == 0
    out = capsys.readouterr().out
    assert "(merged)" in out
    assert "git worm prune" in out


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


def test_switch_print_path_only(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-switch-path"])
    capsys.readouterr()

    result = cli.root_command.execute(["switch", "feat-switch-path", "--path"])
    assert result == 0
    out = capsys.readouterr().out.strip()
    assert out == str(git_repo / ".worktrees" / "feat-switch-path")


def test_switch_finds_worktree_outside_managed_dir(git_repo, tmp_path, capsys):
    external = tmp_path / "external-worktree"
    subprocess.run(
        ["git", "worktree", "add", "-b", "external-branch", str(external), "HEAD"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    cli = _make_cli()

    result = cli.root_command.execute(["switch", "external-branch", "--path"])

    assert result == 0
    assert capsys.readouterr().out.strip() == str(external)


def test_rm_removes_worktree_outside_managed_dir(git_repo, tmp_path, capsys):
    external = tmp_path / "external-remove"
    subprocess.run(
        ["git", "worktree", "add", "-b", "external-remove", str(external), "HEAD"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    cli = _make_cli()

    result = cli.root_command.execute(["rm", "external-remove", "--yes"])

    assert result == 0
    assert not external.exists()


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
    assert cli.root_command.execute(["rm", "feat-e2e", "--yes"]) == 0
    assert not (git_repo / ".worktrees" / "feat-e2e").exists()


def test_prune_merged_removes_merged_worktrees(git_repo, capsys):
    """Prune removes worktrees whose branches are merged into main by default."""
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
    result = cli.root_command.execute(["prune", "--yes"])
    assert result == 0
    assert not wt_path.exists()
    out = capsys.readouterr().out
    assert "feat-merged" in out


def test_prune_removes_recent_missing_worktree(git_repo, capsys):
    cli = _make_cli()
    cli.root_command.execute(["new", "feat-missing"])
    wt_path = git_repo / ".worktrees" / "feat-missing"
    shutil.rmtree(wt_path)

    result = cli.root_command.execute(["prune", "--yes"])

    assert result == 0
    worktrees = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "feat-missing" not in worktrees


def test_prune_merged_keeps_unmerged_worktrees(git_repo, capsys):
    """Prune does not remove worktrees with unmerged commits."""
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
    result = cli.root_command.execute(["prune"])
    assert result == 0
    assert wt_path.exists()
    out = capsys.readouterr().out
    assert "Nothing to prune." in out


def test_prune_no_merged_keeps_merged_worktrees(git_repo, capsys):
    """Prune --no-merged only prunes stale refs, keeping merged worktrees."""
    cli = _make_cli()

    cli.root_command.execute(["new", "feat-kept"])
    wt_path = git_repo / ".worktrees" / "feat-kept"
    (wt_path / "new_file.txt").write_text("feature work")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat work"],
        cwd=wt_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feat-kept"],
        cwd=git_repo, check=True, capture_output=True,
    )

    result = cli.root_command.execute(["prune", "--no-merged", "--yes"])
    assert result == 0
    assert wt_path.exists()
    out = capsys.readouterr().out
    assert "Nothing to prune." in out
    assert "--no-merged" in out


def test_prune_skips_dirty_merged_worktrees(git_repo, capsys):
    """Prune does not remove merged worktrees with uncommitted changes."""
    cli = _make_cli()

    cli.root_command.execute(["new", "feat-dirty"])
    wt_path = git_repo / ".worktrees" / "feat-dirty"
    (wt_path / "new_file.txt").write_text("feature work")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat work"],
        cwd=wt_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feat-dirty"],
        cwd=git_repo, check=True, capture_output=True,
    )
    (wt_path / "uncommitted.txt").write_text("work in progress")

    result = cli.root_command.execute(["prune", "--yes"])
    assert result == 0
    assert wt_path.exists()
    out = capsys.readouterr().out
    assert "uncommitted changes" in out


def test_prune_dry_run_makes_no_changes(git_repo, capsys):
    """Prune --dry-run reports merged worktrees but removes nothing."""
    cli = _make_cli()

    cli.root_command.execute(["new", "feat-dry"])
    wt_path = git_repo / ".worktrees" / "feat-dry"
    (wt_path / "new_file.txt").write_text("feature work")
    subprocess.run(["git", "add", "."], cwd=wt_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat work"],
        cwd=wt_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "merge", "feat-dry"],
        cwd=git_repo, check=True, capture_output=True,
    )

    result = cli.root_command.execute(["prune", "--dry-run"])
    assert result == 0
    assert wt_path.exists()
    out = capsys.readouterr().out
    assert "feat-dry" in out
    assert "dry-run" in out
