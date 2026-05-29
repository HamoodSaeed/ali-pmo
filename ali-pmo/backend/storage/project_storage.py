from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.config import ALLOWED_UPLOAD_EXTENSIONS, OUTPUTS_ROOT, PROJECTS_ROOT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_storage_roots() -> None:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    cleaned = Path(filename).name.replace(" ", "_")
    return cleaned or "uploaded_document"


def project_dir(file_id: str) -> Path:
    return PROJECTS_ROOT / file_id


def upload_dir(file_id: str) -> Path:
    return project_dir(file_id) / "uploads"


def output_dir(file_id: str) -> Path:
    return project_dir(file_id) / "outputs"


def metadata_path(file_id: str) -> Path:
    return project_dir(file_id) / "metadata.json"


def extracted_text_path(file_id: str) -> Path:
    return project_dir(file_id) / "extracted_text.txt"


def analysis_path(file_id: str) -> Path:
    return project_dir(file_id) / "analysis.json"


def plan_path(file_id: str) -> Path:
    return project_dir(file_id) / "project_plan.json"


def parser_status_path(file_id: str) -> Path:
    return project_dir(file_id) / "parser_status.json"


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_metadata(file_id: str) -> dict[str, Any]:
    metadata = read_json(metadata_path(file_id))
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Unknown file_id: {file_id}")
    return metadata


def save_upload(file: UploadFile) -> dict[str, Any]:
    ensure_storage_roots()
    original_name = file.filename or "uploaded_document"
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed}")

    file_id = uuid4().hex
    folder = project_dir(file_id)
    uploads = upload_dir(file_id)
    outputs = output_dir(file_id)
    uploads.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)

    stored_name = safe_filename(original_name)
    stored_path = uploads / stored_name
    with stored_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    metadata = {
        "file_id": file_id,
        "original_filename": original_name,
        "stored_filename": stored_name,
        "extension": extension,
        "content_type": file.content_type,
        "size_bytes": stored_path.stat().st_size,
        "uploaded_at": utc_now(),
        "project_folder": str(folder),
        "upload_path": str(stored_path),
        "parser_status": "pending",
        "outputs": [],
    }
    write_json(metadata_path(file_id), metadata)
    write_json(parser_status_path(file_id), {"status": "pending", "updated_at": utc_now()})
    return metadata


def update_metadata(file_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    metadata = get_metadata(file_id)
    metadata.update(updates)
    metadata["updated_at"] = utc_now()
    write_json(metadata_path(file_id), metadata)
    return metadata


def save_extracted_text(file_id: str, text: str) -> None:
    extracted_text_path(file_id).write_text(text, encoding="utf-8")


def load_extracted_text(file_id: str) -> str | None:
    path = extracted_text_path(file_id)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def save_analysis(file_id: str, analysis: dict[str, Any]) -> None:
    write_json(analysis_path(file_id), analysis)


def load_analysis(file_id: str) -> dict[str, Any] | None:
    return read_json(analysis_path(file_id))


def save_plan(file_id: str, plan: dict[str, Any]) -> None:
    write_json(plan_path(file_id), plan)


def load_plan(file_id: str) -> dict[str, Any] | None:
    return read_json(plan_path(file_id))


def save_parser_status(file_id: str, status: str, details: dict[str, Any] | None = None) -> None:
    payload = {"status": status, "updated_at": utc_now(), "details": details or {}}
    write_json(parser_status_path(file_id), payload)
    update_metadata(file_id, {"parser_status": status})


def list_projects() -> list[dict[str, Any]]:
    ensure_storage_roots()
    projects: list[dict[str, Any]] = []
    for path in PROJECTS_ROOT.glob("*/metadata.json"):
        metadata = read_json(path)
        if metadata:
            projects.append(metadata)
    return sorted(projects, key=lambda item: item.get("uploaded_at", ""), reverse=True)


def resolve_output_file(file_id: str, output_name: str) -> Path:
    allowed_name = Path(output_name).name
    path = output_dir(file_id) / allowed_name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Output not found: {output_name}")
    return path
