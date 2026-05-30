# Ali PMO

Ali PMO is an intelligent project management operating system prototype. It converts messy project documents into structured project control outputs for a Project Manager, PMO team, or executive stakeholder.

The first prototype is local-first and deterministic. It does not call paid AI APIs. It parses uploaded project documents, extracts project intelligence with rule-based logic, generates a WBS project plan, and exports operational files.

## What It Generates

- Structured project intelligence JSON
- Hierarchical project plan
- `project_plan.xlsx`
- `project_plan.csv`
- `raid_log.xlsx`
- `executive_summary.md`
- `weekly_status_update.md`
- `ms_project.xml`

## Architecture

- `frontend/`: React + TypeScript UI built with Vite
- `backend/app/`: FastAPI application and API routes
- `backend/parsers/`: document text extraction
- `backend/extractors/`: deterministic project structure extraction
- `backend/generators/`: project plan and output file generation
- `backend/storage/`: uploaded file folders, text caches, metadata, analysis, and plans
- `backend/outputs/`: reserved output root; generated outputs are stored per project under `backend/storage/projects/{file_id}/outputs`
- `samples/`: sample project documents
- `netlify.toml`: Netlify build configuration for the React frontend

## Backend Setup

From the project root:

```bash
cd ali-pmo/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## Frontend Setup

In a second terminal:

```bash
cd ali-pmo/frontend
npm install
npm run dev
```

The UI runs at:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` calls to the FastAPI backend.

## Tap Billing Setup

Ali PMO includes a Tap Payments checkout flow for a `1.000 OMR` monthly user subscription.

Backend environment variables:

```bash
ALI_PMO_PAYMENT_REQUIRED=true
ALI_PMO_PUBLIC_APP_URL=https://your-netlify-site.netlify.app
ALI_PMO_PUBLIC_API_URL=https://your-ali-pmo-api.example.com
ALI_PMO_CORS_ORIGINS=https://your-netlify-site.netlify.app,http://localhost:5173,http://127.0.0.1:5173
TAP_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxx
TAP_MERCHANT_ID=
TAP_SOURCE_ID=src_all
TAP_SAVE_CARD=true
TAP_PLAN_AMOUNT=1.000
TAP_PLAN_CURRENCY=OMR
TAP_PLAN_INTERVAL_DAYS=30
```

Frontend environment variable:

```bash
VITE_API_BASE_URL=https://your-ali-pmo-api.example.com
```

Important Tap notes:

- Keep `TAP_SECRET_KEY` only on the backend.
- The frontend starts checkout through `POST /api/billing/checkout`.
- Tap redirects users back to `ALI_PMO_PUBLIC_APP_URL` with `tap_id`.
- The frontend calls `GET /api/billing/confirm` to verify the Tap charge before unlocking the app.
- Recurring monthly charging requires Tap Save Card to be enabled on your Tap merchant account. Ali PMO stores Tap customer/card/payment-agreement IDs when Tap returns them, so a future scheduled monthly charge worker can use them.

## Upload A Sample Document

1. Start the backend.
2. Start the frontend.
3. Open `http://127.0.0.1:5173`.
4. Go to Upload.
5. Upload `samples/sample_project_brief.txt`.
6. Click:
   - Parse document
   - Analyze project content
   - Generate project plan
   - Generate outputs
7. Open Output Center and download the generated files.

## API Endpoints

- `GET /api/billing/config`: return billing and Tap configuration status
- `GET /api/billing/status?email=user@example.com`: return subscription status
- `POST /api/billing/checkout`: create a Tap checkout charge
- `GET /api/billing/confirm?tap_id=...&email=...`: verify a Tap payment and activate access
- `POST /api/billing/webhook`: receive Tap payment notifications
- `POST /api/upload`: upload PDF, TXT, DOCX, CSV, or XLSX
- `POST /api/parse/{file_id}`: extract and cache text
- `POST /api/analyze/{file_id}`: extract project intelligence
- `POST /api/generate-plan/{file_id}`: generate WBS project plan
- `POST /api/generate-outputs/{file_id}`: generate export files
- `GET /api/download/{file_id}/{output_name}`: download a generated output
- `GET /api/projects`: list recent projects
- `GET /api/project/{file_id}`: load project snapshot

## Output Storage

Each upload gets a project folder:

```text
backend/storage/projects/{file_id}/
```

Important files:

- `uploads/{original_file}`
- `metadata.json`
- `parser_status.json`
- `extracted_text.txt`
- `analysis.json`
- `project_plan.json`
- `outputs/project_plan.xlsx`
- `outputs/project_plan.csv`
- `outputs/raid_log.xlsx`
- `outputs/executive_summary.md`
- `outputs/weekly_status_update.md`
- `outputs/ms_project.xml`

## Run Tests

```bash
cd ali-pmo/backend
pytest
```

The tests cover:

- PDF text extraction
- TXT extraction
- Project structure extraction
- Project plan generation
- Excel generation
- RAID log generation
- Microsoft Project XML generation

## Deploy Frontend To Netlify

Netlify can host the React frontend. The FastAPI backend should be deployed separately to a Python-capable host such as Render, Railway, Fly.io, or a VPS.

1. Push this repository to GitHub.
2. Create a new Netlify site from Git.
3. Use the included `netlify.toml`, or set:
   - Base directory: `ali-pmo/frontend`
   - Build command: `npm run build`
   - Publish directory: `ali-pmo/frontend/dist`
4. Add this Netlify environment variable:

```bash
VITE_API_BASE_URL=https://your-ali-pmo-api.example.com
```

5. Deploy the FastAPI backend elsewhere and set:

```bash
ALI_PMO_PUBLIC_APP_URL=https://your-netlify-site.netlify.app
ALI_PMO_PUBLIC_API_URL=https://your-ali-pmo-api.example.com
ALI_PMO_CORS_ORIGINS=https://your-netlify-site.netlify.app
ALI_PMO_PAYMENT_REQUIRED=true
TAP_SECRET_KEY=sk_live_or_sk_test_from_tap
```

The backend includes a `Procfile` for hosts that support it:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Known Limitations

- Extraction is deterministic and rule-based; it is designed for predictable prototype behavior, not semantic completeness.
- PDF parsing uses embedded text only. OCR is intentionally not included in this first prototype.
- DOCX, CSV, and XLSX parsing are basic convenience paths.
- Microsoft Project XML is structured for compatibility but should be validated against the target Microsoft Project version before production use.
- Missing details are marked `TBD` or `Assumption` rather than invented.
- Netlify does not persist backend project folders. Keep the current FastAPI backend on a persistent Python host, or replace local storage with object storage before moving document processing into serverless functions.
- Subscription status is currently stored in a JSON file. Use a real database before production.

## Roadmap

- Add optional local or enterprise AI model integration behind the extractor interface.
- Add streaming parser status and visible progress in the UI.
- Add richer table extraction for PDFs and spreadsheets.
- Add SQLite indexing for larger project libraries.
- Add editable project intelligence and project plan screens.
- Add DOCX executive summary export.
- Add resource assignments and calendars to the Microsoft Project XML generator.
- Add authentication and role-based access for PMO teams.
- Add scheduled monthly renewal charging using saved Tap customer/card/payment-agreement IDs.
- Add verified Tap webhook signature validation before production billing.
