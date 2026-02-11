import hashlib
import hmac
import json
from unittest.mock import patch

TEST_SECRET = "test-secret"

VALID_SENTRY_PAYLOAD = {
    "data": {
        "issue": {
            "id": "123",
            "title": "Error: Something broke",
            "culprit": "app.js:42",
            "level": "error",
            "platform": "javascript",
            "permalink": "https://sentry.io/issues/123",
            "metadata": {"type": "Error", "value": "Something broke"},
            "project": {"slug": "voxstore"},
        }
    }
}


def _sign_bytes(body: bytes, secret: str = TEST_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest over raw bytes."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _post_signed(client, url: str, payload: dict, secret: str = TEST_SECRET):
    """POST a JSON payload with a valid HMAC signature computed over the exact bytes sent."""
    body = json.dumps(payload).encode("utf-8")
    signature = _sign_bytes(body, secret)
    return client.post(
        url,
        content=body,
        headers={
            "sentry-hook-signature": signature,
            "content-type": "application/json",
        },
    )


def test_sentry_webhook_valid_signature(client):
    """Valid signature + valid payload -> 200 accepted, pipeline triggered."""
    with patch("autopilot.webhook_server.run_pipeline") as mock_pipeline:
        res = _post_signed(client, "/sentry-webhook", VALID_SENTRY_PAYLOAD)

    assert res.status_code == 200
    assert res.json()["status"] == "accepted"
    mock_pipeline.assert_called_once()


def test_sentry_webhook_invalid_signature(client):
    """Invalid signature -> 403."""
    body = json.dumps(VALID_SENTRY_PAYLOAD).encode("utf-8")
    res = client.post(
        "/sentry-webhook",
        content=body,
        headers={
            "sentry-hook-signature": "bad-signature",
            "content-type": "application/json",
        },
    )

    assert res.status_code == 403


def test_sentry_webhook_missing_signature(client):
    """Missing signature header -> 403."""
    body = json.dumps(VALID_SENTRY_PAYLOAD).encode("utf-8")
    res = client.post(
        "/sentry-webhook",
        content=body,
        headers={"content-type": "application/json"},
    )

    assert res.status_code == 403


def test_sentry_webhook_wrong_secret(client):
    """Signature computed with wrong secret -> 403."""
    body = json.dumps(VALID_SENTRY_PAYLOAD).encode("utf-8")
    signature = _sign_bytes(body, secret="wrong-secret")

    res = client.post(
        "/sentry-webhook",
        content=body,
        headers={
            "sentry-hook-signature": signature,
            "content-type": "application/json",
        },
    )

    assert res.status_code == 403


def test_sentry_webhook_valid_signature_unparseable_payload(client):
    """Valid signature but payload can't be parsed -> 200 ignored."""
    payload = {"data": {"something_else": {}}}
    res = _post_signed(client, "/sentry-webhook", payload)

    assert res.status_code == 200
    assert res.json()["status"] == "ignored"


def test_health_endpoint(client):
    """Health check does not require signature."""
    res = client.get("/health")

    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
