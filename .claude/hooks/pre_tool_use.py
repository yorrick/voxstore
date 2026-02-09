#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.8"
# ///

"""
Pre-tool-use hook for blocking dangerous operations.

Blocks:
- rm -rf commands
- Access to .env files (use .env.sample instead)
"""

import json
import re
import sys


def is_dangerous_rm_command(command: str) -> bool:
    normalized = " ".join(command.lower().split())
    patterns = [
        r"\brm\s+.*-[a-z]*r[a-z]*f",
        r"\brm\s+.*-[a-z]*f[a-z]*r",
        r"\brm\s+--recursive\s+--force",
        r"\brm\s+--force\s+--recursive",
    ]
    for pattern in patterns:
        if re.search(pattern, normalized):
            return True
    return False


def is_env_file_access(tool_name: str, tool_input: dict) -> bool:
    if tool_name in ["Read", "Edit", "Write"]:
        file_path = tool_input.get("file_path", "")
        if ".env" in file_path and not file_path.endswith(".env.sample"):
            return True
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if re.search(r"\b\.env\b(?!\.sample)", command):
            return True
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if is_env_file_access(tool_name, tool_input):
            print(
                "BLOCKED: Access to .env files is prohibited. Use .env.sample instead.",
                file=sys.stderr,
            )
            sys.exit(2)

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            if is_dangerous_rm_command(command):
                print("BLOCKED: Dangerous rm command detected.", file=sys.stderr)
                sys.exit(2)

        sys.exit(0)
    except json.JSONDecodeError:
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
