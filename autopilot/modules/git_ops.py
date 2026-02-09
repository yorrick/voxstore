"""Git operations for autopilot self-healing pipeline."""

import subprocess


def get_current_branch(cwd: str | None = None) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout.strip()


def create_branch(branch_name: str, cwd: str | None = None) -> tuple[bool, str | None]:
    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        if "already exists" in result.stderr:
            result = subprocess.run(
                ["git", "checkout", branch_name],
                capture_output=True,
                text=True,
                cwd=cwd,
            )
            if result.returncode != 0:
                return False, result.stderr
            return True, None
        return False, result.stderr
    return True, None


def checkout_branch(branch_name: str, cwd: str | None = None) -> tuple[bool, str | None]:
    result = subprocess.run(
        ["git", "checkout", branch_name],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return False, result.stderr
    return True, None


def commit_changes(message: str, cwd: str | None = None) -> tuple[bool, str | None]:
    # Check for changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if not result.stdout.strip():
        return True, None  # Nothing to commit

    # Stage all
    result = subprocess.run(
        ["git", "add", "-A"],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return False, result.stderr

    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return False, result.stderr
    return True, None


def push_branch(branch_name: str, cwd: str | None = None) -> tuple[bool, str | None]:
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        return False, result.stderr
    return True, None
