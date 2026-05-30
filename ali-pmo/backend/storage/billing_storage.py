from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import BACKEND_ROOT


BILLING_ROOT = BACKEND_ROOT / "storage" / "billing"
SUBSCRIPTIONS_PATH = BILLING_ROOT / "subscriptions.json"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def read_subscriptions() -> dict[str, Any]:
    if not SUBSCRIPTIONS_PATH.exists():
        return {}
    return json.loads(SUBSCRIPTIONS_PATH.read_text(encoding="utf-8"))


def write_subscriptions(data: dict[str, Any]) -> None:
    BILLING_ROOT.mkdir(parents=True, exist_ok=True)
    SUBSCRIPTIONS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_subscription(email: str) -> dict[str, Any] | None:
    return read_subscriptions().get(normalize_email(email))


def save_subscription(email: str, subscription: dict[str, Any]) -> dict[str, Any]:
    data = read_subscriptions()
    normalized = normalize_email(email)
    payload = {**subscription, "email": normalized, "updated_at": utc_now().isoformat()}
    data[normalized] = payload
    write_subscriptions(data)
    return payload


def is_subscription_active(email: str) -> bool:
    subscription = get_subscription(email)
    if not subscription or subscription.get("status") != "active":
        return False
    provider = subscription.get("provider", "tap")
    if provider == "tap" and str(subscription.get("tap_status", "")).upper() != "CAPTURED":
        return False
    if provider == "lemonsqueezy" and not subscription.get("provider_status"):
        return False

    period_end = subscription.get("current_period_end")
    if not period_end:
        return False

    try:
        return datetime.fromisoformat(period_end) > utc_now()
    except ValueError:
        return False
