# WAIMS Startup Plan: GM Wedge First, WAIMS Suite Later

## Summary
Launch WAIMS as a **basketball operations software startup** with **WAIMS-GM as the beachhead product** for **lower-resource college programs**: D2, NAIA, JUCO, lower-major, and many women’s programs. Position WAIMS-GM as the affordable, basketball-specific alternative to spreadsheets, custom consulting, and enterprise stacks; position WAIMS Python as the broader performance/medical platform that matures behind it and later expands the suite.

The operating principle is:
- **WAIMS-GM** sells first because it has the clearest buyer pain, the easiest demo, and the best “democratized access” story.
- **WAIMS Python** is hardened to near-GM standards so it can become the second paid module, but it should not be the first commercial wedge.

## Business Plan
### Product positioning
- **Category**: basketball decision-support and performance operations software.
- **Primary problem solved**: smaller staffs need structured roster-building, staff reporting, and player-risk workflows without hiring data engineers or buying a full enterprise stack.
- **Direct competitors**: Teamworks GM / Intelligence, Dropback, Synergy for adjacent workflow pieces.
- **Indirect competitors**: spreadsheets, email, consultants, custom-build shops like RevolutionAI-type services.
- **Differentiation**:
  - basketball-specific workflow instead of generic AI services
  - explainable outputs instead of black-box scoring
  - lower setup burden than enterprise tools
  - usable by basketball ops, coaches, sport science, and medical without engineering support
  - explicit privacy boundaries around staff reporting and medical diligence

### Launch packaging
- **Launch product**: WAIMS-GM
- **Behind-the-scenes suite story**: WAIMS
- **Near-term structure**:
  - WAIMS-GM = sellable wedge
  - WAIMS Python = second module / upsell
- **Commercial narrative**:
  - “WAIMS-GM gives smaller basketball staffs a real board, dossier, staff reporting, and recruiting workflow without needing a custom analytics team.”
  - “WAIMS Python adds readiness, athlete monitoring, and role-based staff operations once a program is ready for the broader platform.”

### Initial customer and buyer
- **Primary buyer**: director of basketball operations, GM-equivalent, head coach, recruiting/portal lead.
- **Secondary internal champions**: sport scientist, athletic trainer, ops coordinator, assistant coach.
- **Best first segment**:
  - D2 / NAIA / JUCO men’s and women’s basketball
  - lower-major D1 programs
  - women’s programs where tooling budgets and staffing are often tighter
- **Why this segment**:
  - enterprise competitors are overbuilt or overpriced
  - spreadsheet-driven workflow is still common
  - ROI is easy to explain: faster decisions, fewer missed targets, cleaner staff coordination

### Monetization and pricing
- **Pricing model**: annual team subscription, not per-seat to start.
- **Launch tiers**:
  - `Starter`: WAIMS-GM only, local/demo-safe setup, recruiting + board + dossier + compare + staff reports
  - `Performance Add-On`: WAIMS Python module for readiness, athlete view, coach command center, validation/ingest monitoring
  - `Advisory Setup`: one-time onboarding / workflow configuration / data cleanup
- **Recommended early pricing posture**:
  - price as “affordable department software,” not as consulting
  - keep setup fee optional but available
  - do not lead with custom model-building; lead with workflow and decision support
- **Pilot motion**:
  - 30–45 day pilot
  - one basketball staff
  - one recruiting / portal cycle
  - one clear outcome metric per pilot

### Go-to-market
- **Sales motion**:
  - founder-led outbound to directors of ops, GMs, head coaches, and women’s basketball staffs
  - demo-first, not slide-first
  - use two live flows:
    - WAIMS-GM player evaluation / staff reports / recruiting
    - WAIMS Python coach command center / athlete view / data quality
- **Proof points to sell on**:
  - “Replace spreadsheet chaos with one board and one dossier flow”
  - “Give sport science and medical a structured advisory role without exposing protected records”
  - “Make staffing-light programs look and operate more like well-resourced programs”
- **Partnership direction**:
  - do not depend on partnerships for v1
  - later explore integration/outreach to recruiting ecosystems or sports-service groups once pilots exist

## Product / Implementation Plan
### WAIMS-GM: make it the commercial wedge
- Freeze the top-level navigation around:
  - `Create Evaluation`
  - `Board`
  - `Player Dossier`
  - `Staff Reports`
  - `Compare`
  - `Recruiting`
- Keep role-specific behavior, but not role-specific nav sprawl:
  - GM sees workflow and readouts
  - Sport Science / Medical see the same surfaces with edit permissions where appropriate
- Keep dossier scope narrow:
  - player file only
  - no workflow/reporting clutter
- Keep `Staff Reports` as the place for:
  - prospect research
  - evidence log
  - Med Diligence
  - completed reports
- Keep `Board` as the place for:
  - stage
  - owner
  - next action
  - budget / walk-away logic
  - edit file controls

### WAIMS-GM: next product additions
- Replace flaky `sportsdataverse` dependence with a more reliable NCAA/ESPN stats path.
- Keep CSV/Excel recruiting import as the default intake motion.
- Improve recruiting confidence model:
  - verified stats weighted highest
  - manual scouting/context weighted lower by default
- Add simple recruiting persistence beyond local-only demo state where feasible.
- Add report-ready summaries in `Staff Reports`:
  - one-screen summary cards before full text areas
  - clearer complete/open status

### WAIMS Python: bring it closer to WAIMS-GM maturity
- Add a real **Data Intake** surface, not just hidden validation:
  - latest drop-zone files
  - validation result per lane
  - accepted vs rejected
  - exact reason for rejection
- Keep the current hardening already present:
  - startup health
  - processed file validation
  - section guards
  - status chip
  - ingest audit log
- Add a dedicated **Connector Status** panel:
  - Oura
  - processed model output
  - optional external feeds
  - current fallback mode
- Add a visible **Ingest Audit** workflow:
  - timestamp
  - zone
  - file
  - status
  - rows
  - detail
  - role if/when user-triggered imports are added
- Add a real import-preview/confirm path later:
  - upload or drop file
  - normalize schema
  - show row-level issues
  - accept/reject before data enters production tables
- Tighten all model-language copy:
  - ACWR stays contextual only
  - readiness remains explainable and deterministic
  - injury-risk language stays conservative and non-clinical

### Shared privacy / governance model
- Keep `PRIVACY.md` in both repos as the source of truth.
- Make product boundaries explicit:
  - WAIMS Python = internal athlete/performance system
  - WAIMS-GM = front-office / external prospect system
- `Med Diligence` stays:
  - public-file review only
  - advisory only
  - no protected student medical records
  - no diagnosis / treatment / clearance claims
- Preserve role-based minimum necessary access in both apps.

## Metrics, Validation, and Acceptance
### Product acceptance
- WAIMS-GM acceptance:
  - GM can run full board-to-dossier-to-report workflow without token friction in demo mode
  - staff roles can author reports without seeing unnecessary GM controls
  - recruiting upload is coach-proof for common spreadsheet mistakes
- WAIMS Python acceptance:
  - startup failures are contained and obvious
  - invalid drop-zone files are visible and auditable
  - the app never silently trusts malformed model output
  - role boundaries remain intact

### Business acceptance
- First 3–5 pilots should prove:
  - staffs can use the software without coding help
  - player file and board workflows replace spreadsheet/email fragmentation
  - staff reporting adds decision quality without privacy confusion
- Core startup KPIs:
  - pilot-to-paid conversion
  - weekly active staff users
  - number of active player files / recruiting files
  - number of completed staff reports per month
  - time from intake to final decision

## Assumptions and Defaults
- Beachhead market is **lower-resource college basketball**, not high-major first.
- Packaging is **WAIMS-GM first, WAIMS suite later**.
- WAIMS-GM is the primary commercial product in year 1.
- WAIMS Python is productized in parallel but sold second unless a pilot explicitly demands both.
- The company sells software, not custom consulting, though onboarding/setup can be a paid service.
- `Med Diligence` remains advisory and privacy-bounded; it does not become a medical clearance engine.
- CSV/Excel remains the default recruiting intake path until a more stable stats connector is ready.
