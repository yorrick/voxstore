#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-dotenv",
#     "claude-agent-sdk",
#     "pydantic",
#     "httpx",
# ]
# ///

"""VoxStore Autopilot Sentry Poller.

Polls the Sentry API for unresolved issues, then triggers the self-healing
pipeline for each new issue. Replaces the webhook-based approach (no tunnel needed).

Usage: uv run poller.py

Environment:
- ANTHROPIC_API_KEY: Required for Claude Agent SDK
- SENTRY_AUTH_TOKEN: Required for Sentry API + MCP server
- SENTRY_ORG: Sentry organization slug
- SENTRY_PROJECT: Sentry project slug
- REPO_PATH: Path to the voxstore repository root
- POLL_INTERVAL_SECONDS: Polling interval (default: 300 = 5 minutes)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autopilot.models.sentry_issue import SentryIssue
from autopilot.pipeline import run_pipeline

load_dotenv()

SENTRY_AUTH_TOKEN = os.getenv("SENTRY_AUTH_TOKEN", "")
SENTRY_ORG = os.getenv("SENTRY_ORG", "")
SENTRY_PROJECT = os.getenv("SENTRY_PROJECT", "")
SENTRY_API_URL = os.getenv("SENTRY_API_URL", "https://sentry.io/api/0")
REPO_PATH = os.getenv(
    "REPO_PATH",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))

DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data"
PROCESSED_FILE = DATA_DIR / "processed_issues.json"


async def fetch_unresolved_issues() -> list[SentryIssue]:
    """Fetch unresolved issues from the Sentry API."""
    url = f"{SENTRY_API_URL}/projects/{SENTRY_ORG}/{SENTRY_PROJECT}/issues/"
    params = {"query": "is:unresolved", "limit": 10}
    headers = {"Authorization": f"Bearer {SENTRY_AUTH_TOKEN}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    return [SentryIssue.from_api_response(item) for item in data]


def load_processed_issues() -> dict[str, str]:
    """Load set of already-processed issue IDs with timestamps."""
    if not PROCESSED_FILE.exists():
        return {}
    with open(PROCESSED_FILE) as f:
        return json.load(f)


def mark_issue_processed(issue_id: str) -> None:
    """Add issue ID to the processed set."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    processed = load_processed_issues()
    processed[issue_id] = datetime.now().isoformat()
    with open(PROCESSED_FILE, "w") as f:
        json.dump(processed, f, indent=2)


async def poll_once() -> None:
    """Run one polling cycle: fetch issues, process new ones."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling Sentry for unresolved issues...")

    try:
        issues = await fetch_unresolved_issues()
    except Exception as e:
        print(f"  Error fetching issues: {e}")
        return

    processed = load_processed_issues()
    new_issues = [i for i in issues if i.id not in processed]

    if not new_issues:
        print(f"  No new issues (total unresolved: {len(issues)})")
        return

    print(f"  Found {len(new_issues)} new issue(s)")

    # Process one at a time
    for issue in new_issues:
        print(f"  Processing: {issue.title} (ID: {issue.id})")
        try:
            result = await run_pipeline(issue, REPO_PATH)
            print(f"  Pipeline complete: run_id={result['run_id']}")
        except Exception as e:
            print(f"  Pipeline error: {e}")
        finally:
            mark_issue_processed(issue.id)


async def poll_loop() -> None:
    """Main polling loop. Runs poll_once every POLL_INTERVAL seconds."""
    print("Starting VoxStore Autopilot Poller")
    print(f"  Sentry org: {SENTRY_ORG}")
    print(f"  Sentry project: {SENTRY_PROJECT}")
    print(f"  Repo path: {REPO_PATH}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print(f"  Processed issues file: {PROCESSED_FILE}")
    print()

    while True:
        await poll_once()
        print(f"  Next poll in {POLL_INTERVAL}s...")
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Validate required env vars
    missing = []
    if not SENTRY_AUTH_TOKEN:
        missing.append("SENTRY_AUTH_TOKEN")
    if not SENTRY_ORG:
        missing.append("SENTRY_ORG")
    if not SENTRY_PROJECT:
        missing.append("SENTRY_PROJECT")

    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("Set them in autopilot/.env")
        sys.exit(1)

    try:
        asyncio.run(poll_loop())
    except KeyboardInterrupt:
        print("\nPoller stopped.")
