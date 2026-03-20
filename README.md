# WAIMS-GM

WAIMS-GM is a basketball decision-support prototype built with a Streamlit frontend, a FastAPI backend, and Supabase-backed auth and persistence. The scoring core is deterministic and mode-aware, with optional LLM augmentation reserved for future workflow enhancements rather than core system logic.

## Product Direction

WAIMS-GM is designed as one shared platform that can support multiple basketball contexts:

- `pro_wnba`
- `cbb_high_major`
- `cbb_d2_low_resource`
- `recruiting_only`

The strongest near-term product wedge is lower-resource college basketball, especially D2, NAIA, JUCO, and similarly small-staff environments where explainable roster, portal, and recruiting support is valuable.

## Live Code Map

- Backend API: `app/main.py`
- Frontend UI: `streamlit_app.py`
- Scoring engine: `waims_gm/services/__init__.py`
- Domain models: `waims_gm/domain.py`
- Shared environment config: `app/config.py`

`app/main.py` is the backend source of truth for:

- API models
- auth validation
- persistence helpers
- live endpoint behavior

Files under `app/auth.py`, `app/models.py`, `app/routes/`, and `app/services/` are compatibility wrappers around `app.main` and should not be treated as separate implementations.

## Current Workflow

The app currently supports:

- creating evaluations
- saving evaluations
- listing saved evaluations
- loading dossier/detail views
- filtering and sorting the board
- side-by-side comparison
- dossier markdown export
- dossier Word export with graceful fallback when `python-docx` is unavailable
- comparison brief markdown export

## Architecture

### Streamlit UI

`streamlit_app.py` handles:

- intake form
- decision board
- dossier/detail rendering
- compare mode
- export actions
- environment badge and runtime labeling

### FastAPI backend

`app/main.py` handles:

- `/health`
- `/evaluate`
- `/evaluate-and-save`
- `/evaluations`
- `/evaluations/{evaluation_id}`
- `DELETE /evaluations/{evaluation_id}`

### Supabase

Supabase handles:

- access-token-based auth
- row-level security
- evaluation record persistence
- GM profile persistence

If you need a quick local helper for fetching a Supabase access token, use:

```powershell
python scripts/get_token.py
```

## Environment Profiles

WAIMS-GM now supports explicit `sandbox` and `live` runtime labels through environment variables shared by the frontend and backend.

Available example files:

- `.env.example`
- `.env.sandbox.example`
- `.env.live.example`

Important variables:

- `WAIMS_ENV`
- `WAIMS_ENV_LABEL`
- `API_BASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_AUD`

Recommended setup:

1. Copy `.env.sandbox.example` to `.env` for local and QA work.
2. Copy `.env.live.example` to the deployment platform's secret store for production.
3. Keep sandbox and live pointed at separate Supabase projects whenever possible.
4. Verify the Streamlit header and sidebar show the intended environment before testing or deleting records.

## Run Locally

### First-time setup

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev]
Copy-Item .env.sandbox.example .env
```

Then fill in the Supabase values in `.env`.

### Start the backend

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

### Check backend health

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -Expand Content
```

Expected shape:

```json
{"ok":true,"environment":"sandbox","environment_label":"Sandbox","live":false}
```

### Start the frontend

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

## End-to-End Manual QA

Use this flow to verify Streamlit + FastAPI + Supabase together:

1. Start the backend with the sandbox `.env`.
2. Confirm `/health` reports `sandbox`.
3. Start Streamlit and confirm the header badge and sidebar say `Sandbox`.
4. Fetch a sandbox Supabase token with `python scripts/get_token.py`.
5. Paste the token into the sidebar and click `Load briefing`.
6. Create a new evaluation and confirm the save succeeds.
7. Verify the new evaluation appears on the board.
8. Open the dossier and confirm recommendation, score cards, Decision Lens, and Five Layer Diagnostic render correctly.
9. Download the dossier `.md` file.
10. Download the dossier `.docx` file if Word export is enabled.
11. Select a second player in compare mode and confirm the roster-need call, verdict cards, and component comparison render.
12. Download the comparison brief `.md` file.
13. Delete the selected evaluation and confirm it disappears from the board.

## Tests

The repo includes coverage for:

- mode-aware scoring behavior
- scorecard component schema
- health and evaluate API paths
- mocked save/list/detail/delete lifecycle flows
- reporting and compare/export helpers

Run tests with:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe -m pytest -q
```

## Demo and Sandbox Assets

Useful repo assets for demos and environment setup:

- demo walkthrough: [DEMO_SCRIPT.md](C:/GitHub/waims-gm/DEMO_SCRIPT.md)
- product positioning note: [POSITIONING.md](C:/GitHub/waims-gm/POSITIONING.md)
- Supabase schema and RLS setup: [supabase/waims_gm_schema.sql](C:/GitHub/waims-gm/supabase/waims_gm_schema.sql)
- demo data seeding script: [scripts/seed_demo_data.py](C:/GitHub/waims-gm/scripts/seed_demo_data.py)

Seed the sandbox with repeatable demo players using:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\seed_demo_data.py
```

Preview the demo file set without authenticating:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\seed_demo_data.py --list
```

Preview what a seed run would do without writing any records:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\seed_demo_data.py --dry-run
```

Seed only one targeted demo file by canonical ID or player name:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\seed_demo_data.py --only demo_high_major_portal_guard
```

To replace existing demo rows with the latest seeded set:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\seed_demo_data.py --replace
```

## Preflight Checklist

Before local demos or deployment, run the preflight script:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\preflight.py
```

If the backend is already running, use:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\preflight.py --check-health
```

What it checks:

- required Supabase settings are present
- API URL shape is valid
- live environments are not pointed at localhost
- sandbox/live labels are consistent
- optional `/health` environment check matches the current env

Recommended operator checklist before deploy:

1. Confirm `.env` or deployment secrets match either sandbox or live, not a mix.
2. Run `scripts\preflight.py`.
3. For running services, run `scripts\preflight.py --check-health`.
4. Run the test suite.
5. Verify the Streamlit UI shows the correct environment badge.
6. Verify sandbox and live point at different Supabase projects.

## Live Deployment Target

The cleanest first live shape is:

- Supabase for auth and persistence
- FastAPI deployed as one web service
- Streamlit deployed as a separate web service
- separate sandbox and live env vars

That gives you:

- a real GM-facing live environment
- a safe sandbox for QA and demos
- clean separation between public UI and API runtime

For a first production pass, keep sandbox and live on separate URLs and separate Supabase projects. Do not point sandbox and live at the same tables.

### Render Blueprint

The repo now includes [render.yaml](C:/GitHub/waims-gm/render.yaml), which defines four Render web services:

- `waims-gm-api-sandbox`
- `waims-gm-ui-sandbox`
- `waims-gm-api-live`
- `waims-gm-ui-live`

Notes:

- the UI services reach their matching API services over Render private networking via `API_HOSTPORT`
- backend health checks use `/health`
- Supabase secrets are marked `sync: false` so you fill them in from the Render dashboard

Suggested Render flow:

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the repo.
3. Let Render read `render.yaml`.
4. For `waims-gm-api-sandbox`, set sandbox `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
5. For `waims-gm-api-live`, set live `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
6. Deploy sandbox first and confirm `/health` returns `sandbox`.
7. Open the sandbox UI and confirm the header badge says `Sandbox`.
8. Only after sandbox is verified, deploy and validate the live pair.

If you want to run only one environment at first, delete the unused services from `render.yaml` before creating the Blueprint, or disable those services in the Render dashboard after import.

## Current Priorities

- keep the backend consolidated around `app/main.py`
- expand automated tests as the product grows
- refine mode-specific scoring
- improve meeting-ready compare and reporting workflows
- keep the system LLM-agnostic at the core
