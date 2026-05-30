import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_ROOT = BACKEND_ROOT / "storage" / "projects"
OUTPUTS_ROOT = BACKEND_ROOT / "outputs"

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}
MANDATORY_SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

PREVIEW_CHARACTER_LIMIT = 1800

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALI_PMO_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

PAYMENT_REQUIRED = os.getenv("ALI_PMO_PAYMENT_REQUIRED", "false").lower() == "true"
PUBLIC_APP_URL = os.getenv("ALI_PMO_PUBLIC_APP_URL", "http://127.0.0.1:5173")
PUBLIC_API_URL = os.getenv("ALI_PMO_PUBLIC_API_URL", "http://127.0.0.1:8000")
BILLING_PROVIDER = os.getenv("ALI_PMO_BILLING_PROVIDER", "tap").lower()

TAP_API_BASE_URL = os.getenv("TAP_API_BASE_URL", "https://api.tap.company/v2")
TAP_SECRET_KEY = os.getenv("TAP_SECRET_KEY", "")
TAP_MERCHANT_ID = os.getenv("TAP_MERCHANT_ID", "")
TAP_SOURCE_ID = os.getenv("TAP_SOURCE_ID", "src_all")
TAP_SAVE_CARD = os.getenv("TAP_SAVE_CARD", "true").lower() == "true"
TAP_PLAN_AMOUNT = float(os.getenv("TAP_PLAN_AMOUNT", "1.000"))
TAP_PLAN_CURRENCY = os.getenv("TAP_PLAN_CURRENCY", "OMR")
TAP_PLAN_INTERVAL_DAYS = int(os.getenv("TAP_PLAN_INTERVAL_DAYS", "30"))

LEMONSQUEEZY_API_BASE_URL = os.getenv("LEMONSQUEEZY_API_BASE_URL", "https://api.lemonsqueezy.com/v1")
LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY", "")
LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID", "")
LEMONSQUEEZY_VARIANT_ID = os.getenv("LEMONSQUEEZY_VARIANT_ID", "")
LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
LEMONSQUEEZY_TEST_MODE = os.getenv("LEMONSQUEEZY_TEST_MODE", "true").lower() == "true"
LEMONSQUEEZY_PLAN_AMOUNT_CENTS = int(os.getenv("LEMONSQUEEZY_PLAN_AMOUNT_CENTS", "100"))
LEMONSQUEEZY_PLAN_CURRENCY = os.getenv("LEMONSQUEEZY_PLAN_CURRENCY", "USD")
