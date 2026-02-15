"""Plane webhook handler: HMAC verification and event parsing."""

from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature of a webhook payload.

    Args:
        payload_bytes: Raw request body bytes.
        signature: Signature from the request header.
        secret: Webhook secret configured in MQ DevEngine.

    Returns:
        True if the signature is valid.
    """
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_webhook_event(payload: dict) -> tuple[str, str, dict]:
    """Parse a Plane webhook payload into (event_type, action, data).

    Plane webhooks typically have the structure:
        { "event": "issue", "action": "update", "data": { ... } }

    Returns:
        Tuple of (event_type, action, data).
        Falls back to ("unknown", "unknown", payload) if structure is unexpected.
    """
    event_type = payload.get("event", "unknown")
    action = payload.get("action", "unknown")
    data = payload.get("data", payload)
    return event_type, action, data
