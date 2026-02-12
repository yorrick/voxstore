"""Autonomous bug-fix agent using Claude Code SDK with Sentry MCP server.

Spins up a Claude Code agent that:
1. Investigates the Sentry error (via Sentry MCP server)
2. Explores the codebase to understand context
3. Applies a minimal, focused fix
4. Runs full verification (ruff, pyright, pytest, playwright)
5. Commits, pushes, and creates a PR
"""

import logging
import os

from claude_agent_sdk import ClaudeAgentOptions, query

from autopilot.agents.agent_logging import log_agent_message
from autopilot.models.sentry_issue import SentryIssue

FIX_SYSTEM_PROMPT = """\
You are an autonomous senior developer fixing a production bug. You are working \
in a git worktree on a dedicated branch. Your goal is to investigate the error, \
apply a minimal fix, verify it, and create a pull request.

## Application Context

VoxStore is a voice-powered e-commerce product catalog with:
- A FastAPI backend (app/server/) with SQLite database
- A vanilla JS frontend (app/client/) with voice search via Web Speech API
- E2E tests with Playwright

## Your Workflow

Follow these phases in order. Do NOT skip any phase.

### Phase 1: Investigate the Error

Use the Sentry MCP tools (provided via MCP server) to get full details about the error:
- Fetch the issue details and latest events
- Read the full stacktrace with source context
- Understand error frequency and affected users

IMPORTANT: You MUST use the Sentry MCP tools (e.g. mcp__sentry__get_issue_details, \
mcp__sentry__search_issues) — NEVER make raw curl/HTTP calls to the Sentry API. \
The MCP server is already authenticated and available to you.

### Phase 2: Explore Relevant Code

Read the source files mentioned in the stacktrace and error context:
- Trace the execution path that leads to the error
- Understand the data flow and state that causes the failure
- Identify the root cause (not just the symptom)

### Phase 3: Apply the Fix

Apply the minimal fix needed:
- Only modify files directly related to the error
- Keep changes minimal and focused — do NOT refactor unrelated code
- Do not add new dependencies
- Do not modify test files unless the test itself is wrong
- Follow existing code patterns and conventions

### Phase 4: Verify the Fix

Run the full verification suite. You MUST run ALL of these checks:

For Python changes (app/server/):
```bash
cd app/server && uv run ruff format . && uv run ruff check . && uv run pyright . \
&& uv run pytest -v
```

For Frontend changes (app/client/):
```bash
npx prettier --write "app/client/**/*.{js,css,html}"
```

For ALL changes:
```bash
npx playwright test
```

If any check fails, fix the issue and re-run the checks.

### Phase 5: Commit and Create PR

Once all checks pass:

1. Stage your changes (specific files only, not `git add -A`):
```bash
git add <specific files you changed>
```

2. Commit with a descriptive message:
```bash
git commit -m "fix: <concise description of what was fixed>

Fixed by VoxStore Autopilot
Sentry: <sentry_permalink>"
```

3. Push the branch:
```bash
git push -u origin <current_branch_name>
```

4. Create the PR:
```bash
gh pr create --title "fix: <concise description>" --body "<pr_body>"
```

The PR body should include:
- What error was fixed (with Sentry link)
- Root cause analysis
- What was changed and why
- Verification results

## Important Rules

- Be thorough in your investigation — understand the root cause before fixing
- Make the smallest change that correctly fixes the issue
- Always verify your fix with the full test suite
- If you cannot fix the issue, explain why in detail
- Do not modify CLAUDE.md, README, or configuration files
- Do not push to main — always work on your branch
"""


def _build_fix_prompt(issue: SentryIssue) -> str:
    """Build the initial prompt for the fix agent."""
    return f"""Fix this production error from Sentry:

**Issue ID:** {issue.id}
**Short ID:** {issue.short_id}
**Title:** {issue.title}
**Culprit:** {issue.culprit}
**Level:** {issue.level}
**Occurrences:** {issue.count}
**First seen:** {issue.first_seen}
**Last seen:** {issue.last_seen}
**Sentry URL:** {issue.permalink}

Start by using the Sentry MCP tools to get the full error details and stacktrace \
for issue {issue.short_id}. Then follow your workflow to investigate, fix, verify, \
and create a PR."""


async def run_code_fix_agent(
    issue: SentryIssue,
    worktree_path: str,
    *,
    logger: logging.Logger | None = None,
) -> dict:
    """Run the autonomous fix agent in a worktree.

    The agent has access to:
    - Sentry MCP server (for querying issue details)
    - All standard tools (Read, Write, Edit, Bash, Glob, Grep)
    - gh CLI (for creating PRs)

    Returns a dict with:
        - success: bool
        - summary: str
        - pr_url: str | None
    """
    log = logger or logging.getLogger("autopilot.fix_agent")
    prompt = _build_fix_prompt(issue)

    sentry_token = os.getenv("SENTRY_AUTH_TOKEN", "")
    npx_path = os.getenv(
        "NPX_PATH",
        os.path.expanduser("~/.local/share/fnm/node-versions/v24.13.1/installation/bin/npx"),
    )
    node_bin_dir = os.path.dirname(npx_path)
    mcp_servers: dict = {
        "sentry": {
            "command": npx_path,
            "args": ["-y", "@sentry/mcp-server"],
            "env": {
                "SENTRY_AUTH_TOKEN": sentry_token,
                "PATH": f"{node_bin_dir}:/usr/local/bin:/usr/bin:/bin",
            },
        },
    }

    branch_name = f"autopilot/fix-{issue.id}"
    options = ClaudeAgentOptions(
        model="opus",
        system_prompt=FIX_SYSTEM_PROMPT,
        cwd=worktree_path,
        max_turns=50,
        permission_mode="bypassPermissions",
        mcp_servers=mcp_servers,
        env={"CLAUDE_CODE_TASK_LIST_ID": branch_name},
    )

    summary = ""
    async for message in query(prompt=prompt, options=options):
        text = log_agent_message(message, log)
        if text:
            summary = text

    # Try to extract PR URL from the summary
    pr_url = _extract_pr_url(summary or "")

    return {
        "success": bool(summary and pr_url),
        "summary": summary,
        "pr_url": pr_url,
    }


def _extract_pr_url(text: str) -> str | None:
    """Extract a GitHub PR URL from agent output text."""
    import re

    match = re.search(r"https://github\.com/[^/]+/[^/]+/pull/\d+", text)
    return match.group(0) if match else None
