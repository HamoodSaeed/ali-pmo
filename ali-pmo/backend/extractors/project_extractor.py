from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "project_title": ("project title", "project name", "initiative name", "program name"),
    "background": ("background", "context", "overview", "current state", "business need"),
    "scope": ("scope", "in scope", "out of scope", "project scope"),
    "objectives": ("objectives", "goals", "success objectives", "business objectives"),
    "deliverables": ("deliverables", "outputs", "work products", "key deliverables"),
    "milestones": ("milestones", "timeline", "schedule", "major milestones"),
    "tasks": ("tasks", "activities", "work packages", "action items", "workstreams"),
    "risks": ("risks", "issues", "risk register", "concerns"),
    "assumptions": ("assumptions",),
    "dependencies": ("dependencies", "external dependencies", "dependency"),
    "constraints": ("constraints", "limitations", "boundaries"),
    "stakeholders": ("stakeholders", "roles", "project team", "approvers", "sponsors"),
    "dates": ("dates", "key dates", "deadlines"),
    "acceptance_criteria": ("acceptance criteria", "acceptance", "definition of done"),
    "required_approvals": ("required approvals", "approvals", "approval gates", "sign-off", "signoff"),
}

DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}|"
    r"\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4})\b",
    re.IGNORECASE,
)

DEPENDENCY_PATTERN = re.compile(
    r"\b(subject to|pending|requires|required by|after approval|blocked by|depends on|dependent on|awaiting)\b",
    re.IGNORECASE,
)

RISK_PATTERN = re.compile(r"\b(risk|issue|blocker|threat|delay|impact|could|may|unlikely|concern)\b", re.IGNORECASE)
OWNER_PATTERN = re.compile(r"\b(?:owner|responsible|assigned to|lead|pm|sponsor)\s*[:\-]\s*([^,;\n|]+)", re.IGNORECASE)


def analyze_project_text(file_id: str, text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    sections = split_sections(normalized)
    all_lines = meaningful_lines(normalized)

    extracted: dict[str, Any] = {
        "file_id": file_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "project_title": extract_project_title(sections, all_lines),
        "background": extract_paragraph(sections, "background"),
        "scope": extract_items(sections, "scope"),
        "objectives": extract_items(sections, "objectives"),
        "deliverables": extract_items(sections, "deliverables"),
        "milestones": extract_items(sections, "milestones"),
        "tasks": extract_tasks(sections, all_lines),
        "risks": extract_risks(sections, all_lines),
        "assumptions": extract_items(sections, "assumptions"),
        "dependencies": extract_dependencies(sections, all_lines),
        "constraints": extract_items(sections, "constraints"),
        "stakeholders": extract_stakeholders(sections),
        "dates": extract_dates(normalized),
        "acceptance_criteria": extract_items(sections, "acceptance_criteria"),
        "required_approvals": extract_items(sections, "required_approvals"),
        "missing_information": [],
        "confidence_notes": [],
    }

    add_inferred_sections(extracted, sections, all_lines)
    extracted["missing_information"] = missing_information(extracted)
    extracted["confidence_notes"] = confidence_notes(extracted)
    return extracted


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def meaningful_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = strip_bullet(raw)
        if line and not line.lower().startswith("--- page"):
            lines.append(line)
    return lines


def strip_bullet(line: str) -> str:
    return re.sub(r"^\s*(?:[-*•]|\d+[.)]|[a-z][.)])\s*", "", line.strip(), flags=re.IGNORECASE)


def split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading, inline_value = detect_heading(line)
        if heading:
            current = heading
            sections.setdefault(current, [])
            if inline_value:
                sections[current].append(inline_value)
            continue

        if current:
            sections.setdefault(current, []).append(strip_bullet(line))

    return sections


def detect_heading(line: str) -> tuple[str | None, str | None]:
    candidate = re.sub(r"^\d+(?:\.\d+)*\s+", "", line).strip()
    candidate = candidate.rstrip("#").strip()
    if ":" in candidate:
        left, right = candidate.split(":", 1)
        canonical = canonical_section(left)
        if canonical:
            return canonical, right.strip() or None

    clean = candidate.strip(" :-").lower()
    if len(clean) <= 70:
        canonical = canonical_section(clean)
        if canonical:
            return canonical, None
    return None, None


def canonical_section(value: str) -> str | None:
    clean = re.sub(r"[^a-z0-9 /_-]", "", value.lower()).strip()
    for canonical, aliases in SECTION_ALIASES.items():
        if clean == canonical.replace("_", " ") or clean in aliases:
            return canonical
    return None


def extract_project_title(sections: dict[str, list[str]], lines: list[str]) -> str:
    title_items = sections.get("project_title", [])
    if title_items:
        return title_items[0]

    for line in lines[:12]:
        match = re.search(r"\bproject\s+(?:name|title)\s*[:\-]\s*(.+)", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    for line in lines[:8]:
        if 4 <= len(line) <= 90 and not DEPENDENCY_PATTERN.search(line):
            return line
    return "TBD Project Title"


def extract_paragraph(sections: dict[str, list[str]], key: str) -> str:
    items = sections.get(key, [])
    return " ".join(item for item in items if item).strip()


def extract_items(sections: dict[str, list[str]], key: str) -> list[str]:
    items = []
    for line in sections.get(key, []):
        items.extend(split_compound_line(line))
    return dedupe([item for item in items if is_useful_item(item)])


def split_compound_line(line: str) -> list[str]:
    if "|" in line:
        return [strip_bullet(part) for part in line.split("|")]
    if ";" in line and len(line) > 90:
        return [strip_bullet(part) for part in line.split(";")]
    return [strip_bullet(line)]


def is_useful_item(item: str) -> bool:
    return bool(item and len(item) > 2 and not item.lower().startswith("--- page"))


def extract_tasks(sections: dict[str, list[str]], lines: list[str]) -> list[dict[str, Any]]:
    candidates = [line for line in sections.get("tasks", []) if is_useful_item(line)]
    if not candidates:
        candidates = [
            line
            for line in lines
            if re.search(r"\b(prepare|build|create|configure|review|approve|test|validate|deploy|migrate|design|implement)\b", line, re.IGNORECASE)
        ]

    tasks = []
    for index, candidate in enumerate(dedupe(candidates), start=1):
        tasks.append(
            {
                "id": f"T{index:03d}",
                "name": clean_task_name(candidate),
                "description": candidate,
                "owner": extract_owner(candidate) or "TBD Owner",
                "dependencies": dependency_phrases(candidate),
                "dates": DATE_PATTERN.findall(candidate),
                "status": infer_status(candidate),
                "source": "tasks_section" if sections.get("tasks") else "inferred_from_text",
            }
        )
    return tasks


def clean_task_name(value: str) -> str:
    cleaned = re.split(r"\s+-\s+|\s+\|\s+", value, maxsplit=1)[0].strip()
    cleaned = re.sub(r"\b(owner|responsible|assigned to|lead)\s*[:\-].*", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned[:120] or "TBD Task"


def extract_owner(value: str) -> str | None:
    match = OWNER_PATTERN.search(value)
    if match:
        return match.group(1).strip()
    if "|" in value:
        parts = [part.strip() for part in value.split("|")]
        for part in parts:
            if re.search(r"\b(PMO|IT|Finance|Legal|Vendor|Sponsor|Owner|Manager|Lead)\b", part, re.IGNORECASE):
                return part
    return None


def infer_status(value: str) -> str:
    if re.search(r"\b(blocked|delayed|at risk|issue)\b", value, re.IGNORECASE):
        return "At Risk"
    if re.search(r"\b(done|completed|approved|closed)\b", value, re.IGNORECASE):
        return "Completed"
    if re.search(r"\b(in progress|ongoing|underway)\b", value, re.IGNORECASE):
        return "In Progress"
    return "Not Started"


def extract_risks(sections: dict[str, list[str]], lines: list[str]) -> list[dict[str, Any]]:
    candidates = extract_items(sections, "risks")
    if not candidates:
        candidates = [line for line in lines if RISK_PATTERN.search(line)]

    risks = []
    for index, candidate in enumerate(dedupe(candidates), start=1):
        high_impact = bool(re.search(r"\b(high|critical|blocked|delay|executive|regulatory|budget)\b", candidate, re.IGNORECASE))
        risks.append(
            {
                "id": f"R{index:03d}",
                "description": candidate,
                "owner": extract_owner(candidate) or "TBD Owner",
                "impact": "High" if high_impact else "Medium",
                "probability": "TBD",
                "status": "Open",
                "escalation_required": high_impact,
                "mitigation": "TBD mitigation / action",
            }
        )
    return risks


def extract_dependencies(sections: dict[str, list[str]], lines: list[str]) -> list[dict[str, Any]]:
    candidates = extract_items(sections, "dependencies")
    candidates.extend(line for line in lines if DEPENDENCY_PATTERN.search(line))
    dependencies = []
    for index, candidate in enumerate(dedupe(candidates), start=1):
        blocked = bool(re.search(r"\b(blocked|pending|awaiting)\b", candidate, re.IGNORECASE))
        dependencies.append(
            {
                "id": f"D{index:03d}",
                "description": candidate,
                "owner": extract_owner(candidate) or "TBD Owner",
                "status": "Blocked" if blocked else "Open",
                "escalation_required": blocked,
            }
        )
    return dependencies


def dependency_phrases(value: str) -> list[str]:
    if not DEPENDENCY_PATTERN.search(value):
        return []
    return [value]


def extract_stakeholders(sections: dict[str, list[str]]) -> list[dict[str, str]]:
    stakeholders = []
    for index, item in enumerate(extract_items(sections, "stakeholders"), start=1):
        role = "Stakeholder"
        name = item
        if ":" in item:
            role, name = [part.strip() for part in item.split(":", 1)]
        elif "|" in item:
            parts = [part.strip() for part in item.split("|") if part.strip()]
            if len(parts) >= 2:
                name, role = parts[0], parts[1]
        stakeholders.append({"id": f"S{index:03d}", "name": name, "role": role, "approval_required": "approval" in item.lower()})
    return stakeholders


def extract_dates(text: str) -> list[str]:
    return dedupe([match.group(0) if hasattr(match, "group") else match for match in DATE_PATTERN.finditer(text)])


def add_inferred_sections(extracted: dict[str, Any], sections: dict[str, list[str]], lines: list[str]) -> None:
    if not extracted["deliverables"]:
        extracted["deliverables"] = [
            line for line in lines if re.search(r"\b(deliver|handover|report|dashboard|plan|document|system)\b", line, re.IGNORECASE)
        ][:8]

    if not extracted["milestones"]:
        extracted["milestones"] = [
            line for line in lines if re.search(r"\b(milestone|phase|gate|go-live|launch|deadline|sign-off|approval)\b", line, re.IGNORECASE)
        ][:8]

    if not extracted["required_approvals"]:
        approvals = [line for line in lines if re.search(r"\b(approval|approve|sign-off|signoff|steering committee|sponsor)\b", line, re.IGNORECASE)]
        extracted["required_approvals"] = dedupe(approvals)[:8]


def missing_information(extracted: dict[str, Any]) -> list[str]:
    required = {
        "project_title": "Project title",
        "scope": "Project scope",
        "objectives": "Project objectives",
        "deliverables": "Deliverables",
        "milestones": "Milestones",
        "tasks": "Tasks",
        "stakeholders": "Stakeholders",
        "dates": "Key dates",
        "acceptance_criteria": "Acceptance criteria",
    }
    missing = []
    for key, label in required.items():
        value = extracted.get(key)
        if value in (None, "", [], {}):
            missing.append(label)
    return missing


def confidence_notes(extracted: dict[str, Any]) -> list[str]:
    notes = ["Rule-based deterministic extraction used; no paid AI API dependency."]
    if extracted["missing_information"]:
        notes.append("Missing fields are marked TBD or Assumption in generated outputs.")
    if any(dependency.get("escalation_required") for dependency in extracted["dependencies"]):
        notes.append("Blocked or pending dependencies were flagged for escalation discipline.")
    return notes


def dedupe(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    unique = []
    for item in items:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique
