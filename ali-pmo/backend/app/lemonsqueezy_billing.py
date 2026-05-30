from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException

from app.billing import CheckoutRequest
from app.config import (
    LEMONSQUEEZY_API_BASE_URL,
    LEMONSQUEEZY_API_KEY,
    LEMONSQUEEZY_PLAN_AMOUNT_CENTS,
    LEMONSQUEEZY_PLAN_CURRENCY,
    LEMONSQUEEZY_STORE_ID,
    LEMONSQUEEZY_TEST_MODE,
    LEMONSQUEEZY_VARIANT_ID,
    LEMONSQUEEZY_WEBHOOK_SECRET,
    PUBLIC_APP_URL,
)
from storage.billing_storage import get_subscription, normalize_email, save_subscription, utc_now


ACTIVE_STATUSES = {"active", "on_trial", "paused", "past_due", "unpaid", "cancelled"}


def is_configured() -> bool:
    return bool(LEMONSQUEEZY_API_KEY and LEMONSQUEEZY_STORE_ID and LEMONSQUEEZY_VARIANT_ID and LEMONSQUEEZY_WEBHOOK_SECRET)


async def create_checkout(payload: CheckoutRequest) -> dict[str, Any]:
    if not is_configured():
        raise HTTPException(status_code=503, detail="Lemon Squeezy billing is not fully configured.")

    email = normalize_email(payload.email)
    body = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "custom_price": LEMONSQUEEZY_PLAN_AMOUNT_CENTS,
                "product_options": {
                    "enabled_variants": [int(LEMONSQUEEZY_VARIANT_ID)],
                    "redirect_url": f"{PUBLIC_APP_URL.rstrip('/')}/?payment=return&provider=lemonsqueezy&email={email}",
                },
                "checkout_data": {"email": email, "custom": {"user_email": email}},
                "test_mode": LEMONSQUEEZY_TEST_MODE,
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": str(LEMONSQUEEZY_STORE_ID)}},
                "variant": {"data": {"type": "variants", "id": str(LEMONSQUEEZY_VARIANT_ID)}},
            },
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{LEMONSQUEEZY_API_BASE_URL.rstrip('/')}/checkouts",
            headers={
                "Authorization": f"Bearer {LEMONSQUEEZY_API_KEY}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            json=body,
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    checkout = response.json()["data"]
    attributes = checkout["attributes"]
    save_subscription(
        email,
        {
            "status": "pending",
            "provider": "lemonsqueezy",
            "plan": "monthly_usd",
            "amount": LEMONSQUEEZY_PLAN_AMOUNT_CENTS / 100,
            "currency": LEMONSQUEEZY_PLAN_CURRENCY,
            "checkout_id": checkout["id"],
            "checkout_url": attributes["url"],
            "test_mode": attributes.get("test_mode", LEMONSQUEEZY_TEST_MODE),
        },
    )
    return {
        "checkout_url": attributes["url"],
        "amount": LEMONSQUEEZY_PLAN_AMOUNT_CENTS / 100,
        "currency": LEMONSQUEEZY_PLAN_CURRENCY,
        "test_mode": attributes.get("test_mode", LEMONSQUEEZY_TEST_MODE),
    }


def verify_webhook_signature(raw_body: bytes, signature: str | None) -> None:
    if not LEMONSQUEEZY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Lemon Squeezy webhook secret is not configured.")
    digest = hmac.new(LEMONSQUEEZY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(digest, signature):
        raise HTTPException(status_code=401, detail="Invalid Lemon Squeezy webhook signature.")


def record_webhook(payload: dict[str, Any]) -> dict[str, str]:
    meta = payload.get("meta", {})
    attributes = payload.get("data", {}).get("attributes", {})
    event_name = str(meta.get("event_name", ""))
    email = meta.get("custom_data", {}).get("user_email") or attributes.get("user_email")
    if not email:
        return {"status": "ignored"}

    normalized = normalize_email(email)
    existing = get_subscription(normalized) or {}
    if event_name == "order_created":
        save_subscription(normalized, {**existing, "provider": "lemonsqueezy", "status": "pending", "order_id": payload["data"].get("id")})
        return {"status": "ok"}

    if not event_name.startswith("subscription_"):
        return {"status": "ignored"}

    subscription_status = str(attributes.get("status", "")).lower()
    period_end = attributes.get("ends_at") or attributes.get("renews_at")
    if subscription_status in ACTIVE_STATUSES:
        period_end = period_end or (utc_now() + timedelta(days=30)).isoformat()
        save_subscription(
            normalized,
            {
                **existing,
                "provider": "lemonsqueezy",
                "status": "active",
                "provider_status": subscription_status,
                "current_period_end": parse_period_end(period_end),
                "subscription_id": payload["data"].get("id"),
                "test_mode": attributes.get("test_mode", LEMONSQUEEZY_TEST_MODE),
            },
        )
    else:
        save_subscription(normalized, {**existing, "provider": "lemonsqueezy", "status": "expired", "provider_status": subscription_status})
    return {"status": "ok"}


def parse_period_end(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
