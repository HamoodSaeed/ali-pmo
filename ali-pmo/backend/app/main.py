from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.billing import (
    CheckoutRequest,
    billing_config,
    billing_status,
    confirm_tap_charge,
    create_tap_checkout,
    record_tap_webhook,
    require_active_subscription,
)
from app.config import (
    BILLING_PROVIDER,
    CORS_ORIGINS,
    LEMONSQUEEZY_PLAN_AMOUNT_CENTS,
    LEMONSQUEEZY_PLAN_CURRENCY,
    LEMONSQUEEZY_TEST_MODE,
    PAYMENT_REQUIRED,
)
from app.lemonsqueezy_billing import (
    create_checkout as create_lemonsqueezy_checkout,
    is_configured as is_lemonsqueezy_configured,
    record_webhook as record_lemonsqueezy_webhook,
    verify_webhook_signature,
)
from extractors.project_extractor import analyze_project_text
from generators.output_generator import generate_outputs
from generators.plan_generator import generate_project_plan
from parsers.document_parser import parse_document
from storage.project_storage import (
    get_metadata,
    list_projects,
    load_analysis,
    load_extracted_text,
    load_plan,
    resolve_output_file,
    save_analysis,
    save_plan,
    save_upload,
)


app = FastAPI(title="Ali PMO API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "Ali PMO"}


@app.get("/api/billing/config")
def get_billing_config() -> dict[str, Any]:
    if BILLING_PROVIDER == "lemonsqueezy":
        return {
            "provider": "lemonsqueezy",
            "active_provider": BILLING_PROVIDER,
            "payment_required": PAYMENT_REQUIRED,
            "tap_configured": is_lemonsqueezy_configured(),
            "amount": LEMONSQUEEZY_PLAN_AMOUNT_CENTS / 100,
            "currency": LEMONSQUEEZY_PLAN_CURRENCY,
            "interval": "month",
            "interval_days": 30,
            "save_card_requested": False,
            "test_mode": LEMONSQUEEZY_TEST_MODE,
        }
    return billing_config()


@app.get("/api/billing/status")
def get_billing_status(email: str | None = Query(default=None)) -> dict[str, Any]:
    return billing_status(email)


@app.post("/api/billing/checkout")
async def billing_checkout(payload: CheckoutRequest) -> dict[str, Any]:
    if BILLING_PROVIDER == "lemonsqueezy":
        return await create_lemonsqueezy_checkout(payload)
    return await create_tap_checkout(payload)


@app.get("/api/billing/confirm")
async def billing_confirm(tap_id: str, email: str) -> dict[str, Any]:
    return await confirm_tap_charge(tap_id, email)


@app.post("/api/billing/webhook")
async def billing_webhook(payload: dict[str, Any]) -> dict[str, str]:
    return await record_tap_webhook(payload)


@app.post("/api/billing/lemonsqueezy/webhook")
async def lemonsqueezy_billing_webhook(request: Request) -> dict[str, str]:
    raw_body = await request.body()
    verify_webhook_signature(raw_body, request.headers.get("x-signature"))
    return record_lemonsqueezy_webhook(await request.json())


@app.get("/api/projects")
def projects(request: Request) -> dict[str, Any]:
    require_active_subscription(request)
    return {"projects": list_projects()}


@app.post("/api/upload")
async def upload_document(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    require_active_subscription(request)
    metadata = save_upload(file)
    return {"file_id": metadata["file_id"], "metadata": public_metadata(metadata)}


@app.post("/api/parse/{file_id}")
def parse_uploaded_document(file_id: str, request: Request) -> dict[str, Any]:
    require_active_subscription(request)
    return parse_document(file_id)


@app.post("/api/analyze/{file_id}")
def analyze_uploaded_document(file_id: str, request: Request) -> dict[str, Any]:
    require_active_subscription(request)
    text = load_extracted_text(file_id)
    if text is None:
        parse_document(file_id)
        text = load_extracted_text(file_id)
    if text is None:
        raise HTTPException(status_code=500, detail="Document text extraction did not produce a cache file.")

    analysis = analyze_project_text(file_id, text)
    save_analysis(file_id, analysis)
    return analysis


@app.post("/api/generate-plan/{file_id}")
def generate_plan(file_id: str, request: Request) -> dict[str, Any]:
    require_active_subscription(request)
    analysis = load_analysis(file_id)
    if analysis is None:
        analysis = analyze_uploaded_document(file_id, request)
    plan = generate_project_plan(file_id, analysis)
    save_plan(file_id, plan)
    return plan


@app.post("/api/generate-outputs/{file_id}")
def generate_project_outputs(file_id: str, request: Request) -> dict[str, Any]:
    require_active_subscription(request)
    analysis = load_analysis(file_id)
    if analysis is None:
        analysis = analyze_uploaded_document(file_id, request)
    plan = load_plan(file_id)
    if plan is None:
        plan = generate_plan(file_id, request)
    return generate_outputs(file_id, analysis, plan)


@app.get("/api/project/{file_id}")
def project_snapshot(file_id: str, request: Request) -> dict[str, Any]:
    require_active_subscription(request)
    metadata = get_metadata(file_id)
    return {
        "metadata": public_metadata(metadata),
        "analysis": load_analysis(file_id),
        "plan": load_plan(file_id),
        "has_text_cache": load_extracted_text(file_id) is not None,
    }


@app.get("/api/download/{file_id}/{output_name}")
def download_output(file_id: str, output_name: str, request: Request) -> FileResponse:
    require_active_subscription(request)
    path = resolve_output_file(file_id, output_name)
    return FileResponse(path=path, filename=Path(output_name).name, media_type="application/octet-stream")


def public_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    hidden_keys = {"upload_path"}
    return {key: value for key, value in metadata.items() if key not in hidden_keys}
