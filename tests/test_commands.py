import subprocess

from git_werk import routes
from xclif import Cli


def _make_cli():
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
