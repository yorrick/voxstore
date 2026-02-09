"""Parse Sentry webhook payloads into structured error info for the fix agent."""

from pydantic import BaseModel


class SentryError(BaseModel):
    """Parsed error info from a Sentry webhook."""

    title: str
    message: str
    culprit: str
    level: str
    platform: str
    stacktrace: str
    url: str
    project: str
    event_id: str


def parse_sentry_webhook(payload: dict) -> SentryError | None:
    """Extract structured error info from a Sentry issue webhook payload.

    Sentry sends different webhook formats. This handles the 'issue' alert type,
    which is the most common for new errors.
    """
    # Handle issue alert format
    data = payload.get("data", {})
    event = data.get("event", {})

    if not event:
        # Try the issue format directly
        issue = data.get("issue", {})
        if not issue:
            return None
        return SentryError(
            title=issue.get("title", "Unknown error"),
            message=issue.get("metadata", {}).get("value", ""),
            culprit=issue.get("culprit", "unknown"),
            level=issue.get("level", "error"),
            platform=issue.get("platform", "unknown"),
            stacktrace=_format_issue_stacktrace(issue),
            url=issue.get("permalink", ""),
            project=issue.get("project", {}).get("slug", "unknown"),
            event_id=issue.get("id", ""),
        )

    # Event-based format
    return SentryError(
        title=event.get("title", "Unknown error"),
        message=event.get("message", ""),
        culprit=event.get("culprit", "unknown"),
        level=event.get("level", "error"),
        platform=event.get("platform", "unknown"),
        stacktrace=_format_event_stacktrace(event),
        url=payload.get("url", ""),
        project=payload.get("project_slug", "unknown"),
        event_id=event.get("event_id", ""),
    )


def _format_event_stacktrace(event: dict) -> str:
    """Format stacktrace from a Sentry event payload."""
    lines = []
    exception = event.get("exception", {})
    values = exception.get("values", [])

    for exc in values:
        exc_type = exc.get("type", "Exception")
        exc_value = exc.get("value", "")
        lines.append(f"{exc_type}: {exc_value}")

        stacktrace = exc.get("stacktrace", {})
        frames = stacktrace.get("frames", [])
        for frame in frames:
            filename = frame.get("filename", "?")
            lineno = frame.get("lineno", "?")
            function = frame.get("function", "?")
            context_line = frame.get("context_line", "")
            lines.append(f"  File {filename}, line {lineno}, in {function}")
            if context_line:
                lines.append(f"    {context_line.strip()}")

    return "\n".join(lines) if lines else "No stacktrace available"


def _format_issue_stacktrace(issue: dict) -> str:
    """Format stacktrace from a Sentry issue payload (less detailed)."""
    metadata = issue.get("metadata", {})
    culprit = issue.get("culprit", "")
    value = metadata.get("value", "")
    exc_type = metadata.get("type", "Error")

    lines = [f"{exc_type}: {value}"]
    if culprit:
        lines.append(f"  at {culprit}")

    return "\n".join(lines)
