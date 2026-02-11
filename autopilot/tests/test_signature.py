import hashlib
import hmac

from autopilot.modules.signature import verify_hmac_sha256


def _compute_signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_valid_signature():
    """Correct signature returns True."""
    body = b'{"event": "test"}'
    secret = "my-secret"
    signature = _compute_signature(body, secret)

    assert verify_hmac_sha256(body, secret, signature) is True


def test_invalid_signature():
    """Wrong signature returns False."""
    body = b'{"event": "test"}'
    secret = "my-secret"

    assert verify_hmac_sha256(body, secret, "bad-signature") is False


def test_wrong_secret():
    """Signature computed with a different secret returns False."""
    body = b'{"event": "test"}'
    signature = _compute_signature(body, "correct-secret")

    assert verify_hmac_sha256(body, "wrong-secret", signature) is False


def test_empty_body():
    """Empty body with valid signature returns True."""
    body = b""
    secret = "my-secret"
    signature = _compute_signature(body, secret)

    assert verify_hmac_sha256(body, secret, signature) is True


def test_empty_secret():
    """Empty secret still produces a deterministic HMAC."""
    body = b'{"event": "test"}'
    secret = ""
    signature = _compute_signature(body, secret)

    assert verify_hmac_sha256(body, secret, signature) is True


def test_empty_secret_wrong_signature():
    """Empty secret with wrong signature returns False."""
    body = b'{"event": "test"}'

    assert verify_hmac_sha256(body, "", "wrong") is False
