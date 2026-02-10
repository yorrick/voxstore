"""Git worktree operations for autopilot pipeline."""

import subprocess
from pathlib import Path


def create_worktree(
    issue_id: str,
    repo_root: str,
) -> tuple[bool, str, str | None]:
    """Create a git worktree for fixing a Sentry issue.

    Creates worktree at trees/autopilot/fix-{issue_id} with a new branch.

    Returns (success, worktree_path, error).
    """
    branch_name = f"autopilot/fix-{issue_id}"
    worktree_path = str(Path(repo_root) / "trees" / "autopilot" / f"fix-{issue_id}")

    # Ensure trees/autopilot/ directory exists
    Path(worktree_path).parent.mkdir(parents=True, exist_ok=True)

    # Remove stale worktree if it exists
    if Path(worktree_path).exists():
        success, err = remove_worktree(worktree_path, repo_root)
        if not success:
            return False, worktree_path, f"Failed to remove stale worktree: {err}"

    # Create worktree with new branch from main
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch_name, worktree_path, "main"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        # Branch may already exist — try without -b
        result = subprocess.run(
            ["git", "worktree", "add", worktree_path, branch_name],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return False, worktree_path, result.stderr

    return True, worktree_path, None


def remove_worktree(
    worktree_path: str,
    repo_root: str,
) -> tuple[bool, str | None]:
    """Remove a git worktree and optionally its branch.

    Returns (success, error).
    """
    result = subprocess.run(
        ["git", "worktree", "remove", "--force", worktree_path],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode != 0:
        return False, result.stderr
    return True, None
