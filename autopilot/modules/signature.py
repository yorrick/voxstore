"""HMAC-SHA256 signature verification for Sentry webhooks."""

import hashlib
import hmac
import json
import os

from fastapi import HTTPException, Request

SENTRY_WEBHOOK_SECRET = os.getenv("SENTRY_WEBHOOK_SECRET", "")


def verify_hmac_sha256(body: bytes, secret: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature over a body using a secret.

    Uses timing-safe comparison to prevent timing attacks.
    Returns True if the signature is valid, False otherwise.
    """
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def require_sentry_signature(request: Request) -> dict:
    """FastAPI dependency that verifies Sentry webhook HMAC-SHA256 signature.

    Reads the raw body, computes HMAC-SHA256 with the configured secret,
    and compares against the Sentry-Hook-Signature header.
    Returns the parsed JSON payload if valid.
    """
    if not SENTRY_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    body = await request.body()
    signature = request.headers.get("sentry-hook-signature", "")

    if not verify_hmac_sha256(body, SENTRY_WEBHOOK_SECRET, signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
