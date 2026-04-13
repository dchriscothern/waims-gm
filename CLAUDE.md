# CLAUDE.md — WAIMS-GM

## Environment
This repo supports two explicit runtime environments:
- `sandbox` branch → development and QA work
- `main` branch → live / production-ready

Always confirm which environment you are in before making changes. The Streamlit header and sidebar show the active environment label. Do not treat `main` as a safe place to experiment.

## Sandbox Workflow
For local run commands, sandbox → main process, and Streamlit Cloud setup:
See `C:\GitHub\_docs\STREAMLIT-WORKFLOW.md`

---

## HOW TO APPROACH EVERY TASK

**Before writing any code:**
1. State your interpretation of the task explicitly
2. If ambiguous, list interpretations and ask — do not pick one silently and run
3. Name the specific files you plan to touch and why
4. If a simpler approach exists, say so before starting

**Minimum code rule:**
Write the minimum code that solves the problem. No speculative features, no added configurability that wasn't asked for, no abstractions built for hypothetical future use. The scoring core is intentionally deterministic — do not add complexity to it without being asked.

**Surgical changes only:**
Touch only what the task requires. Do not improve adjacent code, reformat unrelated files, or refactor things that aren't broken. Match existing style. If you notice issues elsewhere, mention them — do not fix them without being asked. Remove imports/variables/functions only if YOUR changes made them unused.

**Verify before finishing:**
For any multi-step task, state success criteria before starting:
- What will be different when this is done?
- What will you check to confirm it worked?
Run `python -m pytest -q` and do a quick UI smoke test on affected views before marking done.

**When confused:**
Stop. Name what's unclear. Ask. The scoring engine, privacy boundaries, and role separation in this repo are intentional — do not change them based on assumptions.

---

## Project

WAIMS-GM is the commercial wedge in the WAIMS product family: a basketball decision-support application for smaller staffs that need a board, dossier, staff-reporting workflow, and recruiting intake without hiring a custom analytics team.

- **Repo:** `C:\GitHub\waims-gm`
- **Primary target market:** D2, NAIA, JUCO, lower-major D1, women's programs
- **Demo mode:** local in-memory, no backend/auth required
- **Full stack:** Streamlit + FastAPI + Supabase

---

## Stack

- **Frontend:** `streamlit_app.py` — intake form, board, dossier, compare, export
- **Backend:** `app/main.py` — FastAPI, all API models, auth validation, persistence helpers, live endpoint behavior
- **Scoring engine:** `waims_gm/services/__init__.py` — deterministic, mode-aware
- **Domain models:** `waims_gm/domain.py`
- **Config:** `app/config.py`

### Source of truth rule
`app/main.py` is the backend source of truth. Files under `app/auth.py`, `app/models.py`, `app/routes/`, and `app/services/` are compatibility wrappers — do not treat them as separate implementations or edit them as if they own the logic.

---

## Core Navigation (freeze this structure)

- `Create Evaluation`
- `Board`
- `Player Dossier`
- `Staff Reports`
- `Compare`
- `Recruiting`

Do not add nav items, rename these, or restructure the top-level flow without being asked.

---

## Scoring Engine — CRITICAL RULES

The scoring core is **intentionally deterministic**, not ML-first.

- Do not add ML or probabilistic scoring to the core engine without explicit direction
- Do not change mode-aware scoring behavior without understanding which modes are affected
- AI/LLM augmentation is reserved for future assistive layers (memo drafting, note cleanup) — not core scoring
- The `Level / Delta` lens is the primary decision framing — do not replace or rename it

**Level / Delta:**
- `Level` = expected contribution band if things go roughly to plan
- `Delta` = outcome band width — how much the bet could swing

Credit: John Chisholm.

---

## Supported Modes

```
Pro / WNBA
CBB High-Major
CBB D2-3 NAIA Juco
Recruiting Only
```

Mode-aware scoring behavior must be tested when changes touch the scoring engine. Run `python -m pytest -q` and verify mode output is consistent.

---

## Role Separation

Three roles operate in demo mode: GM, Sport Science, Medical.

- GM sees workflow and readouts
- Sport Science / Medical see the same surfaces with appropriate edit permissions
- Do not add role-specific nav sprawl — roles share the same nav, permissions differ

---

## Privacy Boundary — DO NOT CROSS

WAIMS-GM is a **front-office decision workspace**, not a medical record system.

- `Med Diligence` = public-file review, movement observations, advisory risk framing for outside prospects only
- No protected student medical records
- No diagnosis, treatment, or clearance claims
- See `PRIVACY.md` for the FERPA boundary

If a task would blur this boundary, stop and ask before proceeding.

---

## Demo Mode

Run interview-safe local demo with no backend or auth dependency:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_bootstrap.ps1
```

Demo mode uses:
- local deterministic scoring
- in-memory demo dossiers
- no bearer token
- no FastAPI requirement
- no Supabase dependency

Full stack local run:

```powershell
# Backend
C:\GitHub\waims-gm\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Frontend
C:\GitHub\waims-gm\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

---

## Validation Commands

```powershell
python -m pytest -q
uvicorn app.main:app --reload
streamlit run streamlit_app.py
```

Preflight check before demos or deployment:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\preflight.py
```

Optional health check once API is running:

```powershell
C:\GitHub\waims-gm\.venv\Scripts\python.exe scripts\preflight.py --check-health
```

---

## Branch and Release Rules

- `sandbox` → active development, QA, feature branches
- `main` → live/production-ready, deployable at all times
- Feature branches: start from `sandbox`, merge back to `sandbox`
- Release: `sandbox → main` only when stable and validated

Do not push directly to `main`. Do not merge to `main` without running validation commands and a UI smoke test.

---

## Environment Config

Use `.env.sandbox.example` for local and QA work. Never commit real `.env` files or Supabase service-role keys.

Key variables: `WAIMS_ENV`, `WAIMS_ENV_LABEL`, `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_AUD`

Use separate Supabase projects for sandbox and live whenever possible.

---

## File Responsibilities

- `streamlit_app.py` → all UI: intake, board, dossier, compare, export, environment badge
- `app/main.py` → backend source of truth: API models, auth, persistence, endpoints
- `waims_gm/services/__init__.py` → scoring engine (deterministic, do not touch casually)
- `waims_gm/domain.py` → domain models
- `app/config.py` → shared environment config

---

## Common Failure Points

- Editing compatibility wrappers (`app/auth.py`, `app/models.py`, `app/routes/`, `app/services/`) as if they own logic — they don't, `app/main.py` does
- Scoring behavior changing across modes after edits — always run tests
- Environment label mismatch (header says sandbox but hitting live Supabase) — check `.env` before testing
- Demo mode breaking due to backend dependency creeping into the no-auth path
- Privacy boundary blur — Med Diligence content becoming clinical or clearance-adjacent

---

## Positioning — Do Not Contradict in UI Copy or Demo Content

WAIMS-GM is:
- an affordable basketball operations product, not a consulting engagement
- an alternative to spreadsheet chaos and overbuilt enterprise stacks
- a workflow product that democratizes board, dossier, staff-report, and recruiting capabilities for programs without dedicated data teams

WAIMS-GM is NOT:
- an enterprise product targeting high-major programs first
- a predictive ML system
- a medical records or clearance system
- a generic AI service

Do not add language to the UI, demo content, or any user-visible copy that contradicts these positions.

---

## Separate Products — Do Not Confuse

- **WAIMS-GM** = this repo. Front-office decision support. Basketball ops, recruiting, dossier, staff reports.
- **WAIMS Python** = `dchriscothern/waims-python`. Athlete monitoring dashboard. Readiness, CMJ/RSI, GPS, z-score baselines. WNBA context.
- **InnerAthlete** = separate repo. Multi-role performance intelligence platform. Blood + DNA + Cognitive pillars.

Never pull WAIMS Python athlete monitoring content, CMJ/force plate language, or InnerAthlete pillar framing into WAIMS-GM.

---

## Key Reference Files

- `DEMO_SCRIPT.md` — walkthrough for demos
- `POSITIONING.md` — product positioning detail
- `PRIVACY.md` — FERPA/privacy boundary
- `docs/ARCHITECTURE.md` — architecture walkthrough
- `supabase/waims_gm_schema.sql` — Supabase schema and RLS setup
- `scripts/seed_demo_data.py` — demo data seeding
- `examples/waims_gm_import_sample.csv` — sample CSV import

---

## Session State

(Update at the end of every session)

**Last completed:**
- [ ]

**Known issues:**
- [ ]

**Next priority:**
- [ ]
