import os
import subprocess
import tempfile

import pytest

from autopilot.modules.worktree_ops import create_worktree, remove_worktree


@pytest.fixture
def temp_git_repo(monkeypatch):
    """Create a temporary git repo with an initial commit for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Prevent git from discovering the parent repo.
        parent = os.path.dirname(tmpdir)
        monkeypatch.setenv("GIT_CEILING_DIRECTORIES", parent)
        # Unset GIT_DIR for subprocess isolation (monkeypatch ensures
        # child processes inherit the ceiling).
        monkeypatch.delenv("GIT_DIR", raising=False)
        monkeypatch.delenv("GIT_WORK_TREE", raising=False)

        def _run(cmd):
            subprocess.run(cmd, cwd=tmpdir, capture_output=True)

        _run(["git", "init", "-b", "main"])
        _run(["git", "config", "user.email", "test@test.com"])
        _run(["git", "config", "user.name", "Test"])
        test_file = os.path.join(tmpdir, "README.md")
        with open(test_file, "w") as f:
            f.write("# Test\n")
        _run(["git", "add", "."])
        _run(["git", "commit", "-m", "init"])

        # Verify init worked in the temp repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == ".git", f"Git init failed — found: {result.stdout.strip()}"

        yield tmpdir


def test_create_worktree(temp_git_repo):
    success, worktree_path, err = create_worktree("test-123", temp_git_repo)
    assert success is True, f"create_worktree failed: {err}"
    assert err is None
    assert os.path.exists(worktree_path)
    assert "trees/autopilot/fix-test-123" in worktree_path

    # Verify the worktree has the expected branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=worktree_path,
    )
    assert result.stdout.strip() == "autopilot/fix-test-123"


def test_remove_worktree(temp_git_repo):
    success, worktree_path, _ = create_worktree("test-456", temp_git_repo)
    assert success is True

    success, err = remove_worktree(worktree_path, temp_git_repo)
    assert success is True
    assert err is None
    assert not os.path.exists(worktree_path)


def test_create_worktree_replaces_stale(temp_git_repo):
    # Create worktree first time
    success, worktree_path, _ = create_worktree("test-789", temp_git_repo)
    assert success is True

    # Remove it
    remove_worktree(worktree_path, temp_git_repo)

    # Create again with same ID — should succeed
    success, worktree_path, err = create_worktree("test-789", temp_git_repo)
    assert success is True
    assert os.path.exists(worktree_path)
