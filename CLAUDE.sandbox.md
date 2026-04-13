# CLAUDE.md — WAIMS-GM (Sandbox)

## Environment: SANDBOX / STAGING

* This is the development and experimentation branch
* Safe to test new features, refactors, and architecture changes
* Breaking changes are acceptable if they improve structure
* Temporary debug code and logging are allowed
* Prioritize speed of iteration over polish
* UI can be rough if functionality is being tested
* Validate here before merging to main

**Active branch:** `sandbox`
**Do not work directly on `main` during development sessions.**

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
Stop. Name what's unclear. Ask. The scoring engine, privacy boundaries, and role separation are intentional — do not change them based on assumptions.

---

## Project

WAIMS-GM is the commercial wedge in the WAIMS product family: a basketball decision-support application for smaller staffs that need a board, dossier, staff-reporting workflow, and recruiting intake without hiring a custom analytics team.

- **Repo:** `C:\GitHub\waims-gm`
- **Sandbox branch:** `sandbox`
- **Primary target market:** D2, NAIA, JUCO, lower-major D1, women's programs
- **Demo mode:** local in-memory, no backend/auth required
- **Full stack:** Streamlit + FastAPI + Supabase

---

## Stack

- **Frontend:** `streamlit_app.py`
- **Backend:** `app/main.py` — source of truth for API models, auth, persistence, endpoints
- **Scoring engine:** `waims_gm/services/__init__.py` — deterministic, mode-aware
- **Domain models:** `waims_gm/domain.py`
- **Config:** `app/config.py`

### Source of truth rule
`app/main.py` is the backend source of truth. Files under `app/auth.py`, `app/models.py`, `app/routes/`, and `app/services/` are compatibility wrappers — do not treat them as separate implementations.

---

## Running Locally in Sandbox

### First-time setup
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev]
Copy-Item .env.sandbox.example .env
```

### Interview-safe demo mode (no backend required)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo_bootstrap.ps1
```

### Full local stack
```powershell
# Terminal 1 — backend
C:\GitHub\waims-gm\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Terminal 2 — frontend
C:\GitHub\waims-gm\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

### Confirm you are in sandbox
Before testing, verify:
1. The Streamlit **header badge** says `Sandbox`
2. The **sidebar** shows `Sandbox`
3. Run `python scripts/preflight.py` — it will confirm environment variables

If the badge shows `Live` or is missing, check your `.env` file:
```
WAIMS_ENV=sandbox
WAIMS_ENV_LABEL=Sandbox
```

---

## Sandbox → Main Workflow

When a feature is ready to ship:

1. Run validation: `python -m pytest -q`
2. Run preflight: `python scripts/preflight.py`
3. Do a full UI smoke test on affected views
4. Confirm no unrelated local changes are bundled
5. Open PR: `sandbox → main`
6. Confirm `main` shows `Live` badge after merge/deploy

**Never push directly to `main`.**

---

## About `codex/gm-sandbox-deploy`

This branch was previously used as a de-facto sandbox/live branch. It is now **legacy**.

- Do not start new work from `codex/gm-sandbox-deploy`
- Active development belongs on `sandbox`
- `main` is the live/production-ready branch
- `codex/gm-sandbox-deploy` should be retired once `sandbox` and `main` are fully adopted

---

## Core Navigation (freeze this structure)

- `Create Evaluation`
- `Board`
- `Player Dossier`
- `Staff Reports`
- `Compare`
- `Recruiting`

Do not add nav items or restructure the top-level flow without being asked.

---

## Scoring Engine — CRITICAL RULES

The scoring core is **intentionally deterministic**, not ML-first.

- Do not add ML or probabilistic scoring to the core engine without explicit direction
- Do not change mode-aware scoring behavior without understanding which modes are affected
- AI/LLM augmentation is reserved for future assistive layers only
- The `Level / Delta` lens is the primary decision framing — do not replace or rename it

---

## Supported Modes

```
Pro / WNBA
CBB High-Major
CBB D2-3 NAIA Juco
Recruiting Only
```

Run `python -m pytest -q` after any scoring engine changes to verify mode output is consistent.

---

## Privacy Boundary — DO NOT CROSS (even in sandbox)

- `Med Diligence` = public-file review, movement observations, advisory risk framing only
- No protected student medical records
- No diagnosis, treatment, or clearance claims
- See `PRIVACY.md` for the FERPA boundary

---

## Validation Commands

```powershell
python -m pytest -q
uvicorn app.main:app --reload
streamlit run streamlit_app.py
python scripts/preflight.py
python scripts/preflight.py --check-health  # once API is running
```

---

## Common Failure Points

- Editing compatibility wrappers as if they own logic — they don't, `app/main.py` does
- Scoring behavior changing across modes after edits — always run tests
- Environment label mismatch (header says sandbox but hitting live Supabase) — check `.env`
- Demo mode breaking due to backend dependency creeping into the no-auth path
- Privacy boundary blur in Med Diligence content

---

## Separate Products — Do Not Confuse

- **WAIMS-GM** = this repo. Front-office decision support. Basketball ops, recruiting, dossier, staff reports.
- **WAIMS Python** = `dchriscothern/waims-python`. Athlete monitoring. Readiness, CMJ/RSI, GPS, z-score.
- **InnerAthlete** = separate repo. Blood + DNA + Cognitive platform.

Never pull WAIMS Python or InnerAthlete content into WAIMS-GM.

---

## Session State

(Update at the end of every session)

**Last completed:**
- [ ]

**Known issues:**
- [ ]

**Next priority:**
- [ ]
