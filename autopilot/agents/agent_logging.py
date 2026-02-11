"""Shared logging for agent message streams."""

import logging

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


def _tool_detail(block: ToolUseBlock) -> str:
    """Extract a concise detail string from a tool call's input."""
    inp = block.input or {}
    name = block.name

    if name in ("Read", "Write", "Edit", "NotebookEdit"):
        return inp.get("file_path") or inp.get("notebook_path") or ""
    if name in ("Glob",):
        return inp.get("pattern", "")
    if name in ("Grep",):
        return inp.get("pattern", "")
    if name == "Bash":
        cmd = inp.get("command", "")
        # First line, truncated
        first_line = cmd.split("\n")[0][:120]
        return first_line
    if name == "Task":
        return inp.get("description", "")
    if name == "TodoWrite":
        return ""
    # MCP tools (e.g. mcp__sentry__get_issue_details) — extract useful params
    if name.startswith("mcp__"):
        parts = [f"{k}={v}" for k, v in inp.items() if v and k != "regionUrl"]
        return ", ".join(parts) if parts else ""
    return ""


def log_agent_message(message: object, logger: logging.Logger) -> str | None:
    """Log an agent message and return text content if present.

    Logs tool usage, tool results, and assistant text as they stream in.
    Returns the text content of the message (for capturing the final summary).
    """
    text = None

    if isinstance(message, ResultMessage):
        result = message.result if hasattr(message, "result") else str(message)
        text = result if isinstance(result, str) else str(result)
        logger.info("Agent finished")

    elif isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                text = block.text
                # Log first 200 chars of text to keep logs readable
                preview = text[:200].replace("\n", " ")
                if len(text) > 200:
                    preview += "..."
                logger.info("Agent: %s", preview)
            elif isinstance(block, ToolUseBlock):
                detail = _tool_detail(block)
                if detail:
                    logger.info("Agent tool: %s — %s", block.name, detail)
                else:
                    logger.info("Agent tool: %s", block.name)
            elif isinstance(block, ToolResultBlock):
                pass  # tool results are noisy, skip

    return text
