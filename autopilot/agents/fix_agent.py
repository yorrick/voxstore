"""Fix Agent - Uses Claude Agent SDK to analyze a Sentry error and create a fix."""

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

from autopilot.modules.sentry_parser import SentryError

FIX_SYSTEM_PROMPT = """\
You are a senior developer fixing a production bug in the VoxStore application.

VoxStore is a voice-powered e-commerce product catalog with:
- A FastAPI backend (app/server/) with SQLite database
- A vanilla JS frontend (app/client/) with voice search

You will receive a Sentry error report. Your job is to:
1. Read the relevant source files to understand the context
2. Identify the root cause of the error
3. Apply the minimal fix needed — do NOT refactor or change unrelated code
4. Verify your fix makes sense

IMPORTANT:
- Only modify the files that are directly causing the error
- Keep changes minimal and focused
- Do not add new dependencies
- Do not modify test files unless the test itself is wrong
"""


async def run_fix_agent(error: SentryError, repo_path: str) -> dict:
    """Run the fix agent to analyze and fix a Sentry error.

    Returns a dict with:
        - success: bool
        - summary: str (what was fixed)
        - files_changed: list[str]
    """
    prompt = f"""Fix this production error captured by Sentry:

**Error:** {error.title}
**Message:** {error.message}
**Culprit:** {error.culprit}
**Level:** {error.level}
**Platform:** {error.platform}

**Stacktrace:**
```
{error.stacktrace}
```

**Sentry URL:** {error.url}

Analyze the error, read the relevant source files, and apply a minimal fix.
After fixing, briefly summarize what you changed and why.
"""

    options = ClaudeAgentOptions(
        system_prompt=FIX_SYSTEM_PROMPT,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        cwd=repo_path,
        max_turns=20,
        permission_mode="acceptEdits",
    )

    summary = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            summary = message.result if hasattr(message, "result") else str(message)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    summary = block.text  # Keep updating to get the last text

    return {
        "success": bool(summary),
        "summary": summary,
    }
