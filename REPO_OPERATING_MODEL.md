# WAIMS Repo Operating Model

This document standardizes branch usage, release flow, and cleanup priorities
across both WAIMS repos:

- `C:\GitHub\waims-python`
- `C:\GitHub\waims-gm`

## Branch Roles

Use the same branch model in both repos:

- `main`: live / production-ready branch
- `sandbox`: integration branch for active development
- short-lived feature branches: branch off `sandbox`, merge back into `sandbox`

## Release Flow

1. Start new work from `sandbox`.
2. Open feature PRs into `sandbox`.
3. Validate on `sandbox`.
4. Open PR `sandbox -> main` when the change set is stable.
5. Treat `main` as deployable at all times.

## Branch Protection

Recommended GitHub settings for both repos:

### `main`

- require pull request before merge
- require at least 1 approval
- require branch to be up to date before merge
- require status checks to pass
- block direct pushes
- restrict force pushes
- restrict branch deletion

### `sandbox`

- require pull request before merge for larger changes
- allow maintainers to merge validated feature branches
- block force pushes
- keep deletion restricted

## Deployment Convention

### WAIMS Python

- `main` should be the live/deploy branch
- `sandbox` should be the integration branch
- merge `sandbox -> main` to ship

### WAIMS GM

- set GitHub default branch to `main`
- keep `sandbox` as the integration branch
- treat `codex/gm-sandbox-deploy` as legacy once branch/default settings are updated

## Current State

### WAIMS Python

- `main` exists and is the GitHub default branch
- `sandbox` exists remotely and locally
- latest support cleanup work was staged on `sandbox`

### WAIMS GM

- `main` exists remotely and locally
- `sandbox` exists remotely and locally
- `codex/gm-sandbox-deploy` currently still exists and has been acting like the default/live branch

## Release Checklist

Before merging `sandbox -> main`:

1. Run the repo test/validation commands.
2. Do one quick UI smoke test on the affected views.
3. Confirm no unrelated local changes are being bundled.
4. Confirm docs/config reflect the shipped behavior.

## Validation Commands

### WAIMS Python

```bash
python healthcheck.py --quick
pytest test_waims.py -q -k "not db"
pytest test_oura_integration.py -q
streamlit run dashboard.py
```

### WAIMS GM

```bash
python -m pytest -q
uvicorn app.main:app --reload
streamlit run streamlit_app.py
```

## Cleanup Backlog

### Highest Priority

#### WAIMS Python

- Merge `sandbox -> main` so live and integration are aligned again.
- Retire or archive older long-lived `codex/*` branches once they are no longer needed.
- Keep `healthcheck.py` as the authoritative pre-demo check path.

#### WAIMS GM

- Change GitHub default branch from `codex/gm-sandbox-deploy` to `main`.
- Start using `sandbox` for active work and reserve `main` for live-ready state.
- Eventually retire `codex/gm-sandbox-deploy` once branch hygiene is complete.

### Medium Priority

#### WAIMS Python

- Review older `codex/*` branches and delete/archive stale ones.
- Keep support docs aligned with the actual workflow files and branch model.
- Audit support scripts periodically so setup and healthcheck guidance stay current.

#### WAIMS GM

- Continue reducing `app/main.py` monolith size by extracting logic only when the
  extracted module becomes the actual source of truth.
- Keep compatibility modules thin and explicit.
- Audit remaining docs so they describe the live path instead of historical layouts.

### Low Priority

#### WAIMS Python

- Consolidate or archive older portfolio/demo artifacts if they are no longer useful.

#### WAIMS GM

- Clean up legacy branch names and optional docs once the new branch model is fully adopted.

## Team Rule of Thumb

If a change is not ready for live, it belongs on `sandbox`.
If a change is ready for live, it gets merged from `sandbox` into `main`.
