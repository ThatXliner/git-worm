import os
import subprocess

import pytest

from git_werk import routes
from xclif import Cli


@pytest.fixture(scope="module")
def cli():
    return Cli.from_routes(routes)


@pytest.fixture(scope="module")
def root(cli):
    return cli.root_command


@pytest.fixture()
def git_repo(tmp_path):
    """Create a temporary git repo with an initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    readme = repo / "README.md"
    readme.write_text("hello")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )
    old_cwd = os.getcwd()
    os.chdir(repo)
    yield repo
    os.chdir(old_cwd)
