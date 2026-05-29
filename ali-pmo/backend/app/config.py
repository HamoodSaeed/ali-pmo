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

TAP_API_BASE_URL = os.getenv("TAP_API_BASE_URL", "https://api.tap.company/v2")
TAP_SECRET_KEY = os.getenv("TAP_SECRET_KEY", "")
TAP_MERCHANT_ID = os.getenv("TAP_MERCHANT_ID", "")
TAP_SOURCE_ID = os.getenv("TAP_SOURCE_ID", "src_all")
TAP_SAVE_CARD = os.getenv("TAP_SAVE_CARD", "true").lower() == "true"
TAP_PLAN_AMOUNT = float(os.getenv("TAP_PLAN_AMOUNT", "0.050"))
TAP_PLAN_CURRENCY = os.getenv("TAP_PLAN_CURRENCY", "OMR")
TAP_PLAN_INTERVAL_DAYS = int(os.getenv("TAP_PLAN_INTERVAL_DAYS", "30"))
