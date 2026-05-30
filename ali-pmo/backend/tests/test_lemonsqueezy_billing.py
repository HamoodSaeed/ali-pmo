import hashlib
import hmac
from datetime import timedelta

import pytest
from fastapi import HTTPException

from app import lemonsqueezy_billing
from storage import billing_storage


def test_verify_webhook_signature_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setattr(lemonsqueezy_billing, "LEMONSQUEEZY_WEBHOOK_SECRET", "test-secret")

    with pytest.raises(HTTPException) as exc_info:
        lemonsqueezy_billing.verify_webhook_signature(b"{}", "invalid")

    assert exc_info.value.status_code == 401


def test_verify_webhook_signature_accepts_valid_signature(monkeypatch) -> None:
    monkeypatch.setattr(lemonsqueezy_billing, "LEMONSQUEEZY_WEBHOOK_SECRET", "test-secret")
    payload = b'{"event":"subscription_created"}'
    signature = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()

    lemonsqueezy_billing.verify_webhook_signature(payload, signature)


def test_lemonsqueezy_active_subscription_unlocks_access(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(billing_storage, "BILLING_ROOT", tmp_path)
    monkeypatch.setattr(billing_storage, "SUBSCRIPTIONS_PATH", tmp_path / "subscriptions.json")
    period_end = (billing_storage.utc_now() + timedelta(days=30)).isoformat()
    billing_storage.save_subscription(
        "user@example.com",
        {
            "status": "active",
            "provider": "lemonsqueezy",
            "provider_status": "active",
            "current_period_end": period_end,
        },
    )

    assert billing_storage.is_subscription_active("user@example.com") is True
