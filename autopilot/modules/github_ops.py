"""GitHub operations via gh CLI for autopilot pipeline."""

import json
import os
import subprocess


def _gh_env() -> dict | None:
    """Get environment with GitHub token if available."""
    pat = os.getenv("GITHUB_PAT")
    if not pat:
        return None
    return {"GH_TOKEN": pat, "PATH": os.environ.get("PATH", "")}


def _repo_path() -> str:
    """Get owner/repo from git remote."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=True,
    )
    url = result.stdout.strip()
    return url.replace("https://github.com/", "").replace(".git", "")


def create_pr(
    branch: str,
    title: str,
    body: str,
    cwd: str | None = None,
) -> tuple[str | None, str | None]:
    """Create a PR. Returns (pr_url, error)."""
    repo = _repo_path()
    result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
        ],
        capture_output=True,
        text=True,
        env=_gh_env(),
        cwd=cwd,
    )
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout.strip(), None


def get_pr_diff(pr_number: str) -> str | None:
    """Get the diff for a PR."""
    repo = _repo_path()
    result = subprocess.run(
        ["gh", "pr", "diff", pr_number, "--repo", repo],
        capture_output=True,
        text=True,
        env=_gh_env(),
    )
    if result.returncode == 0:
        return result.stdout
    return None


def get_pr_checks(pr_number: str) -> list[dict]:
    """Get CI check statuses for a PR."""
    repo = _repo_path()
    result = subprocess.run(
        [
            "gh",
            "pr",
            "checks",
            pr_number,
            "--repo",
            repo,
            "--json",
            "name,state",
        ],
        capture_output=True,
        text=True,
        env=_gh_env(),
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return []


def merge_pr(
    pr_number: str,
    method: str = "squash",
) -> tuple[bool, str | None]:
    """Merge a PR. Returns (success, error)."""
    repo = _repo_path()

    # Check if mergeable
    result = subprocess.run(
        [
            "gh",
            "pr",
            "view",
            pr_number,
            "--repo",
            repo,
            "--json",
            "mergeable,mergeStateStatus",
        ],
        capture_output=True,
        text=True,
        env=_gh_env(),
    )
    if result.returncode != 0:
        return False, f"Failed to check PR status: {result.stderr}"

    status = json.loads(result.stdout)
    if status.get("mergeable") != "MERGEABLE":
        return False, f"PR not mergeable: {status.get('mergeStateStatus', 'unknown')}"

    # Merge
    result = subprocess.run(
        [
            "gh",
            "pr",
            "merge",
            pr_number,
            "--repo",
            repo,
            f"--{method}",
            "--body",
            "Auto-merged by VoxStore Autopilot after passing all checks.",
        ],
        capture_output=True,
        text=True,
        env=_gh_env(),
    )
    if result.returncode != 0:
        return False, result.stderr
    return True, None


def add_pr_comment(pr_number: str, comment: str) -> bool:
    """Add a comment to a PR."""
    repo = _repo_path()
    result = subprocess.run(
        [
            "gh",
            "pr",
            "comment",
            pr_number,
            "--repo",
            repo,
            "--body",
            comment,
        ],
        capture_output=True,
        text=True,
        env=_gh_env(),
    )
    return result.returncode == 0


def get_pr_number_for_branch(branch: str) -> str | None:
    """Get PR number for a branch."""
    repo = _repo_path()
    result = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--head",
            branch,
            "--json",
            "number",
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
        env=_gh_env(),
    )
    if result.returncode == 0:
        prs = json.loads(result.stdout)
        if prs:
            return str(prs[0]["number"])
    return None
