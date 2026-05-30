# AGENTS.md

This file guides future Codex sessions working on Ali PMO.

## Product Principle

Ali PMO is not a chatbot. It is an executive-level project management operating system that turns unstructured project documents into structured control outputs. Keep the product focused on clarity, ownership, dependency control, escalation discipline, phase control, and concise executive reporting.

## Architecture

- `frontend/`: React + TypeScript Vite app.
- `backend/app/`: FastAPI app and HTTP endpoints.
- `backend/parsers/`: document extraction. PDF extraction uses PyMuPDF. TXT extraction is mandatory.
- `backend/extractors/`: deterministic rule-based project intelligence extraction.
- `backend/generators/`: project plan, Excel, CSV, Markdown, RAID, and Microsoft Project XML generation.
- `backend/storage/`: project-folder storage, metadata, parser status, text cache, analysis, plan JSON, and generated outputs.
- `backend/app/billing.py`: Tap checkout, payment confirmation, webhook recording, and payment-gate logic.
- `backend/app/lemonsqueezy_billing.py`: Lemon Squeezy hosted checkout and signed subscription webhook handling.
- `samples/`: sample input documents for demos and manual testing.
- `netlify.toml`: frontend deployment config for Netlify.

## Coding Standards

- Keep backend logic modular. API routes should orchestrate storage, parsing, extraction, planning, and output generation.
- Do not add paid API dependencies for the default prototype path.
- Use `TBD` or `Assumption` for missing information. Do not invent exact owners, dates, budgets, approvals, or dependencies.
- Preserve deterministic behavior in tests.
- Keep frontend UI professional, dense enough for PMO work, and focused on the actual workflow.
- Prefer small typed functions over broad utility modules.
- Keep Tap secret keys backend-only. Never expose `TAP_SECRET_KEY` in frontend code.
- Keep Lemon Squeezy API keys and webhook signing secrets backend-only. Never expose them in frontend code.
- Treat billing JSON storage as prototype-only. Move subscriptions to a database before production.

## Run Backend

```bash
cd ali-pmo/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

## Run Frontend

```bash
cd ali-pmo/frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Run Tests

```bash
cd ali-pmo/backend
pytest
```

## Billing And Deployment

- Frontend Netlify builds use `VITE_API_BASE_URL` to call the deployed FastAPI backend.
- Backend CORS is controlled by `ALI_PMO_CORS_ORIGINS`.
- Set `ALI_PMO_PAYMENT_REQUIRED=true` to enforce active subscription checks on project endpoints.
- Tap checkout uses `TAP_SECRET_KEY`, `TAP_SOURCE_ID`, `TAP_PLAN_AMOUNT=1.000`, and `TAP_PLAN_CURRENCY=OMR`.
- Tap recurring billing requires Save Card activation on the merchant account. Store Tap Customer ID, Card ID, and Payment Agreement ID from successful payments for scheduled renewals.
- Before production, add Tap webhook signature validation and real authentication.

## Output Generation Rules

- `project_plan.xlsx` and `project_plan.csv` must contain WBS ID, phase, task name, description, start date, end date, duration, owner, status, predecessor, milestone flag, and notes.
- `raid_log.xlsx` must contain Risk, Assumption, Issue, and Dependency-ready columns.
- `executive_summary.md` must stay decision-oriented and include Missing Information.
- `weekly_status_update.md` must include Date, Overall Status, Key Message, Progress table, Risks / Blockers, and Next Actions.
- `ms_project.xml` should keep Microsoft Project-compatible structure: metadata, calendar placeholder, task hierarchy, dates, milestones, predecessor links, and resources where available.

## Ali PMO Operating Logic

- Clarity first: every generated task needs a clear name and outcome.
- Ownership: missing owners become `TBD Owner`.
- Dependency control: flag phrases such as `subject to`, `pending`, `requires`, `after approval`, and `blocked by`.
- Escalation discipline: high-impact risks and blocked dependencies should be highlighted.
- Phase control: group work into Initiation, Planning, Design, Implementation, Testing, Validation, and Closure wherever possible.
- Executive reporting: summaries should be concise, decision-oriented, and explicit about missing information.

## Future AI Integration

Add model-based extraction behind a new extractor interface without removing the deterministic extractor. The deterministic path should remain available for tests, offline demos, and auditability.
