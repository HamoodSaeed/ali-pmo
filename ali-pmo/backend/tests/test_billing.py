from datetime import timedelta

from app.billing import validate_successful_charge
from storage import billing_storage


def test_validate_successful_charge_rejects_wrong_amount() -> None:
    charge = {
        "id": "chg_test",
        "amount": 0.050,
        "currency": "OMR",
        "metadata": {"user_email": "user@example.com"},
    }

    assert "amount mismatch" in validate_successful_charge(charge, "user@example.com", "chg_test")


def test_validate_successful_charge_accepts_expected_amount() -> None:
    charge = {
        "id": "chg_test",
        "amount": 1.000,
        "currency": "OMR",
        "metadata": {"user_email": "user@example.com"},
    }

    assert validate_successful_charge(charge, "user@example.com", "chg_test") is None


def test_subscription_requires_captured_tap_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(billing_storage, "BILLING_ROOT", tmp_path)
    monkeypatch.setattr(billing_storage, "SUBSCRIPTIONS_PATH", tmp_path / "subscriptions.json")

    period_end = (billing_storage.utc_now() + timedelta(days=30)).isoformat()
    billing_storage.save_subscription(
        "user@example.com",
        {
            "status": "active",
            "tap_status": "AUTHORIZED",
            "current_period_end": period_end,
        },
    )

    assert billing_storage.is_subscription_active("user@example.com") is False
