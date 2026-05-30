from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from app.config import (
    PAYMENT_REQUIRED,
    PUBLIC_API_URL,
    PUBLIC_APP_URL,
    TAP_API_BASE_URL,
    TAP_MERCHANT_ID,
    TAP_PLAN_AMOUNT,
    TAP_PLAN_CURRENCY,
    TAP_PLAN_INTERVAL_DAYS,
    TAP_SAVE_CARD,
    TAP_SECRET_KEY,
    TAP_SOURCE_ID,
)
from storage.billing_storage import get_subscription, is_subscription_active, normalize_email, save_subscription, utc_now


CAPTURED_STATUSES = {"CAPTURED"}
FAILED_STATUSES = {"ABANDONED", "CANCELLED", "FAILED", "DECLINED", "RESTRICTED", "VOID", "TIMEDOUT", "UNKNOWN"}


class CheckoutRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    phone_country_code: str = Field(default="968", max_length=6)
    phone_number: str | None = Field(default=None, max_length=24)


def billing_config() -> dict[str, Any]:
    return {
        "payment_required": PAYMENT_REQUIRED,
        "tap_configured": bool(TAP_SECRET_KEY),
        "amount": TAP_PLAN_AMOUNT,
        "currency": TAP_PLAN_CURRENCY,
        "interval": "month",
        "interval_days": TAP_PLAN_INTERVAL_DAYS,
        "save_card_requested": TAP_SAVE_CARD,
    }


def current_plan_code() -> str:
    amount_part = f"{TAP_PLAN_AMOUNT:.3f}".replace(".", "_")
    return f"monthly_{TAP_PLAN_CURRENCY.lower()}_{amount_part}"


def billing_status(email: str | None) -> dict[str, Any]:
    if not email:
        return {"active": not PAYMENT_REQUIRED, "email": None, "subscription": None, "payment_required": PAYMENT_REQUIRED}

    normalized = normalize_email(email)
    subscription = get_subscription(normalized)
    return {
        "active": is_subscription_active(normalized) or not PAYMENT_REQUIRED,
        "email": normalized,
        "subscription": subscription,
        "payment_required": PAYMENT_REQUIRED,
    }


def require_active_subscription(request: Request) -> None:
    if not PAYMENT_REQUIRED:
        return
    email = request.headers.get("x-ali-user-email") or request.query_params.get("email")
    if not email or not is_subscription_active(email):
        raise HTTPException(status_code=402, detail="Active Ali PMO subscription required.")


async def create_tap_checkout(payload: CheckoutRequest) -> dict[str, Any]:
    if not TAP_SECRET_KEY:
        raise HTTPException(status_code=503, detail="TAP_SECRET_KEY is not configured on the backend.")

    email = normalize_email(payload.email)
    transaction_reference = f"ali-pmo-{uuid4().hex[:18]}"
    redirect_url = f"{PUBLIC_APP_URL.rstrip('/')}/?payment=return&email={email}"
    post_url = f"{PUBLIC_API_URL.rstrip('/')}/api/billing/webhook"
    should_save_card = TAP_SAVE_CARD and bool(payload.phone_number)

    customer: dict[str, Any] = {
        "first_name": payload.first_name.strip() or "Ali",
        "last_name": payload.last_name.strip() or "PMO User",
        "email": email,
    }
    if payload.phone_number:
        customer["phone"] = {"country_code": payload.phone_country_code, "number": payload.phone_number}

    charge_payload: dict[str, Any] = {
        "amount": TAP_PLAN_AMOUNT,
        "currency": TAP_PLAN_CURRENCY,
        "customer_initiated": True,
        "threeDSecure": True,
        "save_card": should_save_card,
        "description": f"Ali PMO monthly subscription - {TAP_PLAN_AMOUNT:.3f} {TAP_PLAN_CURRENCY} per user",
        "metadata": {
            "product": "ali-pmo",
            "plan": current_plan_code(),
            "billing_interval": "month",
            "user_email": email,
        },
        "reference": {"transaction": transaction_reference, "order": "ali-pmo-monthly"},
        "customer": customer,
        "source": {"id": TAP_SOURCE_ID},
        "redirect": {"url": redirect_url},
        "post": {"url": post_url},
    }
    if TAP_MERCHANT_ID:
        charge_payload["merchant"] = {"id": TAP_MERCHANT_ID}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{TAP_API_BASE_URL.rstrip('/')}/charges/",
            headers={"Authorization": f"Bearer {TAP_SECRET_KEY}", "accept": "application/json", "content-type": "application/json", "lang_code": "en"},
            json=charge_payload,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    charge = response.json()
    transaction_url = charge.get("transaction", {}).get("url")
    if not transaction_url:
        raise HTTPException(status_code=502, detail="Tap did not return a checkout transaction URL.")

    save_subscription(
        email,
        {
            "status": "pending",
            "plan": current_plan_code(),
            "amount": TAP_PLAN_AMOUNT,
            "currency": TAP_PLAN_CURRENCY,
            "tap_charge_id": charge.get("id"),
            "tap_reference": transaction_reference,
            "checkout_url": transaction_url,
            "save_card_requested": should_save_card,
            "created_at": utc_now().isoformat(),
        },
    )

    return {
        "checkout_url": transaction_url,
        "tap_charge_id": charge.get("id"),
        "amount": TAP_PLAN_AMOUNT,
        "currency": TAP_PLAN_CURRENCY,
        "save_card_requested": should_save_card,
    }


async def confirm_tap_charge(tap_id: str, email: str) -> dict[str, Any]:
    if not TAP_SECRET_KEY:
        raise HTTPException(status_code=503, detail="TAP_SECRET_KEY is not configured on the backend.")

    normalized = normalize_email(email)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{TAP_API_BASE_URL.rstrip('/')}/charges/{tap_id}",
            headers={"Authorization": f"Bearer {TAP_SECRET_KEY}", "accept": "application/json", "lang_code": "en"},
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    charge = response.json()
    tap_status = str(charge.get("status", "")).upper()
    validation_error = validate_successful_charge(charge, normalized, tap_id)
    if tap_status not in CAPTURED_STATUSES or validation_error:
        save_subscription(
            normalized,
            {
                **(get_subscription(normalized) or {}),
                "status": "payment_failed" if tap_status in FAILED_STATUSES or validation_error else "pending",
                "tap_status": tap_status,
                "tap_charge_id": charge.get("id", tap_id),
                "tap_amount": charge.get("amount"),
                "tap_currency": charge.get("currency"),
                "failure_reason": validation_error or f"Tap payment is not captured. Current status: {tap_status or 'unknown'}",
            },
        )
        raise HTTPException(status_code=402, detail=validation_error or f"Tap payment is not captured. Current status: {tap_status or 'unknown'}")

    now = utc_now()
    subscription = save_subscription(
        normalized,
        {
            **(get_subscription(normalized) or {}),
            "status": "active",
            "plan": current_plan_code(),
            "amount": TAP_PLAN_AMOUNT,
            "currency": TAP_PLAN_CURRENCY,
            "started_at": now.isoformat(),
            "current_period_end": (now + timedelta(days=TAP_PLAN_INTERVAL_DAYS)).isoformat(),
            "tap_status": "CAPTURED",
            "tap_charge_id": charge.get("id", tap_id),
            "tap_amount": charge.get("amount"),
            "tap_currency": charge.get("currency"),
            "tap_customer_id": charge.get("customer", {}).get("id"),
            "tap_card_id": charge.get("card", {}).get("id"),
            "tap_payment_agreement_id": charge.get("payment_agreement", {}).get("id"),
        },
    )
    return {"active": True, "subscription": subscription}


async def record_tap_webhook(payload: dict[str, Any]) -> dict[str, str]:
    email = payload.get("metadata", {}).get("user_email") or payload.get("customer", {}).get("email")
    if not email:
        return {"status": "ignored"}
    tap_status = str(payload.get("status", "")).upper()
    validation_error = validate_successful_charge(payload, normalize_email(email), str(payload.get("id", "")))
    if tap_status in CAPTURED_STATUSES and not validation_error:
        now = utc_now()
        save_subscription(
            email,
            {
                **(get_subscription(email) or {}),
                "status": "active",
                "plan": current_plan_code(),
                "amount": TAP_PLAN_AMOUNT,
                "currency": TAP_PLAN_CURRENCY,
                "started_at": now.isoformat(),
                "current_period_end": (now + timedelta(days=TAP_PLAN_INTERVAL_DAYS)).isoformat(),
                "tap_status": "CAPTURED",
                "tap_charge_id": payload.get("id"),
                "tap_amount": payload.get("amount"),
                "tap_currency": payload.get("currency"),
                "tap_customer_id": payload.get("customer", {}).get("id"),
                "tap_card_id": payload.get("card", {}).get("id"),
                "tap_payment_agreement_id": payload.get("payment_agreement", {}).get("id"),
            },
        )
    else:
        save_subscription(
            email,
            {
                **(get_subscription(email) or {}),
                "status": "payment_failed" if tap_status in FAILED_STATUSES or validation_error else "pending",
                "tap_status": tap_status,
                "tap_charge_id": payload.get("id"),
                "tap_amount": payload.get("amount"),
                "tap_currency": payload.get("currency"),
                "failure_reason": validation_error or f"Tap payment is not captured. Current status: {tap_status or 'unknown'}",
            },
        )
    return {"status": "ok"}


def validate_successful_charge(charge: dict[str, Any], email: str, tap_id: str) -> str | None:
    if charge.get("id") and charge.get("id") != tap_id:
        return "Tap charge ID mismatch."

    charge_currency = str(charge.get("currency", "")).upper()
    if charge_currency != TAP_PLAN_CURRENCY.upper():
        return f"Tap currency mismatch. Expected {TAP_PLAN_CURRENCY}, got {charge_currency or 'unknown'}."

    try:
        charge_amount = Decimal(str(charge.get("amount")))
        expected_amount = Decimal(f"{TAP_PLAN_AMOUNT:.3f}")
    except Exception:
        return "Tap amount is missing or invalid."

    if charge_amount != expected_amount:
        return f"Tap amount mismatch. Expected {expected_amount} {TAP_PLAN_CURRENCY}, got {charge_amount} {charge_currency}."

    metadata_email = charge.get("metadata", {}).get("user_email")
    customer_email = charge.get("customer", {}).get("email")
    charge_email = normalize_email(metadata_email or customer_email or email)
    if charge_email != normalize_email(email):
        return "Tap customer email mismatch."

    return None
