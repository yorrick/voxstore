#!/usr/bin/env -S uv run
# /// script
# dependencies = ["fastapi", "uvicorn", "python-dotenv", "claude-agent-sdk", "pydantic"]
# ///

"""
VoxStore Autopilot Webhook Server

Receives Sentry and GitHub webhooks, triggers the self-healing pipeline.
Exposed via Cloudflare Tunnel so Sentry/GitHub can reach it.

Usage: uv run webhook_server.py

Environment:
- PORT: Server port (default: 8002)
- REPO_PATH: Path to the voxstore repository
- ANTHROPIC_API_KEY: Required for Claude Agent SDK
- SENTRY_WEBHOOK_SECRET: Required for verifying Sentry webhook signatures
"""

import asyncio
import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autopilot.models.sentry_issue import SentryIssue
from autopilot.modules.sentry_parser import parse_sentry_webhook
from autopilot.modules.signature import require_sentry_signature
from autopilot.pipeline import run_pipeline

load_dotenv()

PORT = int(os.getenv("PORT", "8002"))
REPO_PATH = os.getenv("REPO_PATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SENTRY_WEBHOOK_SECRET = os.getenv("SENTRY_WEBHOOK_SECRET", "")

LOG_FORMAT = "[%(asctime)s] %(levelname)s %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATEFMT, level=logging.INFO)
# Apply same format to uvicorn's access and error loggers
for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    uv_logger = logging.getLogger(name)
    uv_logger.handlers.clear()
    uv_logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT))
    uv_logger.addHandler(handler)

logger = logging.getLogger("autopilot.webhook")

app = FastAPI(title="VoxStore Autopilot", description="Self-healing webhook server")

# Track active pipeline runs by issue title to deduplicate webhooks
_active_pipelines: set[str] = set()


def _on_pipeline_done(task: asyncio.Task, issue_key: str) -> None:  # type: ignore[type-arg]
    """Log unhandled exceptions from background pipeline tasks and clean up tracking."""
    _active_pipelines.discard(issue_key)
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error("Pipeline task failed: %s", exc, exc_info=exc)


def _sentry_error_to_issue(error) -> SentryIssue:
    """Convert a legacy SentryError to SentryIssue for the new pipeline."""
    return SentryIssue(
        id=error.event_id,
        title=error.title,
        culprit=error.culprit,
        level=error.level,
        status="unresolved",
        first_seen="",
        last_seen="",
        count=1,
        permalink=error.url,
        short_id="",
        metadata={},
    )


@app.post("/webhook/sentry")
async def sentry_webhook(payload: dict = Depends(require_sentry_signature)):
    """Handle Sentry issue alert webhooks."""
    try:
        error = parse_sentry_webhook(payload)

        if not error:
            return {"status": "ignored", "reason": "Could not parse Sentry payload"}

        logger.info("Received Sentry alert: %s", error.title)
        logger.info("  Culprit: %s", error.culprit)
        logger.info(
            "  Level: %s | Platform: %s | Project: %s", error.level, error.platform, error.project
        )
        logger.info("  Event ID: %s", error.event_id)
        logger.info("  URL: %s", error.url or "(none)")
        logger.info("  Message: %s", error.message or "(none)")
        if error.stacktrace and error.stacktrace != "No stacktrace available":
            for line in error.stacktrace.splitlines():
                logger.info("  Stacktrace: %s", line)

        issue = _sentry_error_to_issue(error)

        # Deduplicate: skip if a pipeline is already running for this issue
        issue_key = error.title
        if issue_key in _active_pipelines:
            logger.info("Pipeline already running for '%s', skipping duplicate", issue_key)
            return {"status": "skipped", "reason": "Pipeline already running for this issue"}

        _active_pipelines.add(issue_key)

        # Run pipeline in background so we return 200 immediately
        task = asyncio.create_task(run_pipeline(issue, REPO_PATH))
        task.add_done_callback(lambda t: _on_pipeline_done(t, issue_key))

        return {
            "status": "accepted",
            "error_title": error.title,
            "message": "Pipeline started",
        }

    except Exception:
        logger.exception("Error processing Sentry webhook")
        return {"status": "error", "message": "Internal server error"}


@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Handle GitHub webhook events (for future use)."""
    try:
        event_type = request.headers.get("X-GitHub-Event", "")
        _ = await request.json()

        logger.info("Received GitHub webhook: event=%s", event_type)

        # For now, just acknowledge. Can be extended to handle:
        # - check_run completed (retry merge)
        # - pull_request_review (re-evaluate merge)
        return {"status": "acknowledged", "event": event_type}

    except Exception:
        logger.exception("Error processing GitHub webhook")
        return {"status": "error", "message": "Internal server error"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "voxstore-autopilot",
        "repo_path": REPO_PATH,
    }


if __name__ == "__main__":
    if not SENTRY_WEBHOOK_SECRET:
        logger.error("SENTRY_WEBHOOK_SECRET is required but not set.")
        logger.error("Set it in your .env file or as an environment variable.")
        sys.exit(1)

    logger.info("Starting VoxStore Autopilot on port %d", PORT)
    logger.info("Sentry webhook: POST /webhook/sentry")
    logger.info("GitHub webhook: POST /webhook/github")
    logger.info("Health check:   GET /health")
    logger.info("Repo path:      %s", REPO_PATH)

    uvicorn.run(app, host="0.0.0.0", port=PORT)
