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

import hashlib
import re
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


def _copy_db_dir(repo_root: Path, worktree_dir: Path) -> None:
    """Copy app/server/db/ (SQLite DB + embeddings cache) to the worktree."""
    src = repo_root / "app/server/db"
    if not src.is_dir():
        return
    dst = worktree_dir / "app/server/db"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    print(
        f"  Copied app/server/db/ ({len(list(dst.iterdir()))} files)", file=sys.stderr
    )


def _branch_port(branch: str) -> int:
    """Derive a deterministic port in 8001-8999 from the branch name."""
    h = int(hashlib.sha1(branch.encode()).hexdigest(), 16)
    return 8001 + (h % 999)


def _patch_env_var(env_file: Path, key: str, value: str) -> None:
    """Replace a KEY=value line in an env file."""
    if not env_file.exists():
        return
    text = env_file.read_text()
    new_text = re.sub(
        rf"(^.*{re.escape(key)}=).*", rf"\g<1>{value}", text, flags=re.MULTILINE
    )
    if new_text != text:
        env_file.write_text(new_text)
        print(f"  Patched {key}={value} in {env_file.name}", file=sys.stderr)


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
    _copy_db_dir(repo_root, worktree_dir)
    _patch_env_var(worktree_dir / ".env", "CLAUDE_CODE_TASK_LIST_ID", branch)
    port = _branch_port(branch)
    _patch_env_var(worktree_dir / "app/server/.env", "BACKEND_PORT", str(port))

    print(f"\nWorktree ready: trees/{branch}", file=sys.stderr)
    print("Run:", file=sys.stderr)
    print(f"  wt {branch}", file=sys.stderr)

    print(f'cd "{worktree_dir}"')


if __name__ == "__main__":
    main()
