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
"""

import asyncio
import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autopilot.modules.sentry_parser import parse_sentry_webhook
from autopilot.pipeline import run_pipeline

load_dotenv()

PORT = int(os.getenv("PORT", "8002"))
REPO_PATH = os.getenv("REPO_PATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="VoxStore Autopilot", description="Self-healing webhook server")


@app.post("/sentry-webhook")
async def sentry_webhook(request: Request):
    """Handle Sentry issue alert webhooks."""
    try:
        payload = await request.json()
        error = parse_sentry_webhook(payload)

        if not error:
            return {"status": "ignored", "reason": "Could not parse Sentry payload"}

        print(f"Received Sentry alert: {error.title}")
        print(f"Culprit: {error.culprit}")
        print(f"Level: {error.level}")

        # Run pipeline in background so we return 200 immediately
        asyncio.create_task(run_pipeline(error, REPO_PATH))

        return {
            "status": "accepted",
            "error_title": error.title,
            "message": "Pipeline started",
        }

    except Exception as e:
        print(f"Error processing Sentry webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/gh-webhook")
async def github_webhook(request: Request):
    """Handle GitHub webhook events (for future use — e.g., re-trigger on check failure)."""
    try:
        event_type = request.headers.get("X-GitHub-Event", "")
        _ = await request.json()

        print(f"Received GitHub webhook: event={event_type}")

        # For now, just acknowledge. Can be extended to handle:
        # - check_run completed (retry merge)
        # - pull_request_review (re-evaluate merge)
        return {"status": "acknowledged", "event": event_type}

    except Exception as e:
        print(f"Error processing GitHub webhook: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "voxstore-autopilot",
        "repo_path": REPO_PATH,
    }


if __name__ == "__main__":
    print(f"Starting VoxStore Autopilot on port {PORT}")
    print("Sentry webhook: POST /sentry-webhook")
    print("GitHub webhook: POST /gh-webhook")
    print("Health check:   GET /health")
    print(f"Repo path:      {REPO_PATH}")

    uvicorn.run(app, host="0.0.0.0", port=PORT)
