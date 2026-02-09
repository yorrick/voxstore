#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Post-tool-use hook for running code quality checks on edited files.

Runs after Edit or Write tool calls:
- Python files: ruff format, ruff check --fix, pyright
- JS files in app/client/: prettier --write
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Python project directories with their own pyproject.toml
PYTHON_PROJECT_DIRS = ["app/server", "autopilot"]


def get_project_root() -> Path:
    if "CLAUDE_PROJECT_DIR" in os.environ:
        return Path(os.environ["CLAUDE_PROJECT_DIR"])
    return Path(__file__).parent.parent.parent


def get_python_project_context(file_path: str) -> tuple[Path, str] | None:
    project_root = get_project_root()
    for project_dir in PYTHON_PROJECT_DIRS:
        prefix = f"{project_dir}/"
        if file_path.startswith(prefix):
            project_path = project_root / project_dir
            relative_path = file_path[len(prefix) :]
            return project_path, relative_path
    return None


def run_command(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=25
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def run_python_checks(project_dir: Path, relative_path: str) -> None:
    print(f"Running checks on {project_dir.name}/{relative_path}...")

    print("  Formatting with ruff...")
    rc, stdout, stderr = run_command(
        ["uv", "run", "ruff", "format", relative_path], project_dir
    )
    if stdout:
        print(stdout)
    if stderr and rc != 0:
        print(stderr)

    print("  Linting with ruff...")
    rc, stdout, stderr = run_command(
        ["uv", "run", "ruff", "check", "--fix", relative_path], project_dir
    )
    if stdout:
        print(stdout)
    if stderr and rc != 0:
        print(stderr)

    print("  Type checking with pyright...")
    rc, stdout, stderr = run_command(
        ["uv", "run", "pyright", relative_path], project_dir
    )
    if stdout:
        print(stdout)
    if stderr and rc != 0:
        print(stderr)

    print(f"✓ Checks complete for {project_dir.name}/{relative_path}")


def run_js_checks(project_root: Path, file_path: str) -> None:
    print(f"Running prettier on {file_path}...")
    rc, stdout, stderr = run_command(
        ["npx", "prettier", "--write", file_path], project_root
    )
    if stdout:
        print(stdout)
    if stderr and rc != 0:
        print(stderr)
    print(f"✓ Formatted {file_path}")


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        project_root = get_project_root()

        # Make path relative to project root
        if file_path.startswith(str(project_root)):
            file_path = str(Path(file_path).relative_to(project_root))

        # Python files
        if file_path.endswith(".py"):
            context = get_python_project_context(file_path)
            if context:
                project_dir, relative_path = context
                run_python_checks(project_dir, relative_path)
            sys.exit(0)

        # JS/CSS files in client
        if file_path.startswith("app/client/") and file_path.endswith(
            (".js", ".css", ".html")
        ):
            run_js_checks(project_root, file_path)
            sys.exit(0)

        sys.exit(0)

    except json.JSONDecodeError:
        sys.exit(0)
    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
