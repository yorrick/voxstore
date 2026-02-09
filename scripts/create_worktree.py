#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Create a git worktree and copy environment files.

Creates a worktree under trees/<branch> and copies .env files.

Outputs a cd command to stdout. Use the fish wrapper:

    wt my-feature

Usage:
    ./scripts/create_worktree.py <branch>
"""

import shutil
import subprocess
import sys
from pathlib import Path


def _get_repo_root() -> Path:
    """Get the git repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Error: not inside a git repository.", file=sys.stderr)
        sys.exit(1)
    return Path(result.stdout.strip())


def _copy_env_files(repo_root: Path, worktree_dir: Path) -> None:
    """Copy .env files from the main repo to the worktree."""
    env_locations = [
        "",  # root .env
        "app/server",
    ]
    for loc in env_locations:
        src = repo_root / loc / ".env" if loc else repo_root / ".env"
        dst = worktree_dir / loc / ".env" if loc else worktree_dir / ".env"
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  Copied {src.relative_to(repo_root)}", file=sys.stderr)
        else:
            print(f"  Skipped {loc or '.'}/{'.env'} (not found)", file=sys.stderr)


def main() -> None:
    """Entry point."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: create_worktree.py <branch>", file=sys.stderr)
        sys.exit(1 if len(sys.argv) != 2 else 0)

    branch = sys.argv[1]
    repo_root = _get_repo_root()
    worktree_dir = repo_root / "trees" / branch

    if worktree_dir.exists():
        print(f"Worktree already exists: trees/{branch}", file=sys.stderr)
        print(f'cd "{worktree_dir}"')
        sys.exit(0)

    print(f"Creating worktree: trees/{branch}", file=sys.stderr)
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_dir), "-b", branch],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "worktree", "add", str(worktree_dir), branch],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                f"Error creating worktree: {result.stderr.strip()}",
                file=sys.stderr,
            )
            sys.exit(1)

    print("Copying environment files...", file=sys.stderr)
    _copy_env_files(repo_root, worktree_dir)

    print(f"\nWorktree ready: trees/{branch}", file=sys.stderr)
    print("Run:", file=sys.stderr)
    print(f"  wt {branch}", file=sys.stderr)

    print(f'cd "{worktree_dir}"')


if __name__ == "__main__":
    main()
