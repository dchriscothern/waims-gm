\# CLAUDE.md



\## Environment: SANDBOX / STAGING



\* This is a development and experimentation environment

\* Safe to test new features, refactors, and architecture changes

\* Breaking changes are acceptable if they improve structure

\* Temporary debug code and logging are allowed

\* Prioritize speed of iteration over polish

\* UI can be rough if functionality is being tested

\* Validate ideas here before promoting to production



\---



\## Project



WAIMS (Wellness and Injury Management System) is a Python + Streamlit athlete monitoring dashboard for performance staff. It tracks readiness, flags injury risk, and manages load for a 12-player anonymized women's basketball roster. Currently a portfolio/demo tool modeled on a WNBA context. V1 uses synthetic demo data.



Live URL: \[https://waims-python-zzikytfewmqiwwfhrdajwo.streamlit.app/]

Repo: dchriscothern/waims-python



\---



\## Stack



\* Frontend: Streamlit

\* Database: SQLite (local), Supabase (future)

\* Visualization: Plotly

\* ML: Random Forest (train\_models.py)

\* Hosting: Streamlit Cloud via GitHub



\---



\## File Roles



\* dashboard.py → app entry point, controls tab routing

\* \*\_tab.py → UI layer only (no heavy data logic)

\* \*\_module.py → calculations, transformations, metrics

\* train\_models.py → model training only (offline, not runtime)

\* model\_validation.py → validation logic only

\* data\_quality.py → input checks and validation rules

\* improved\_gauges.py → reusable UI components

\* research\_context.py → research citations and supporting evidence



Rule:

UI files should not contain heavy data processing.



\---



\## Tab Structure (8 tabs)



1\. Roster Overview

2\. Athlete Profile

3\. GPS \& Load

4\. Availability \& Injuries

5\. Force Plate (CMJ/RSI)

6\. Z-Score Baselines

7\. Research Context

8\. \[Update name when finalized]



\---



\## Data Flow



Data

→ preprocessing (z\_score\_module, data\_quality)

→ modeling (optional, train\_models)

→ tab-level logic

→ UI rendering (Streamlit)



Principles:



\* Data transformation happens before UI

\* UI only displays processed outputs

\* Models are not run inside UI render loop



\---



\## Stable Rules



\* Keep coach-facing outputs simple and practical

\* Keep sport scientist outputs more technical

\* Do not casually change evidence-based thresholds

\* Prefer editing real source files instead of generated outputs

\* WAIMS\_Coach\_Overview.pdf should remain a true one-pager

\* WAIMS\_SportScientist\_Overview.pdf can be multi-page

\* Emoji-free UI

\* Text-only status labels

\* Left-border color coding + horizontal fill bars

\* Z-score personal baselines alongside absolute thresholds (not either/or)

\* Force plate (CMJ/RSI) is primary fatigue signal, not GPS alone

\* Research citations prioritize female/basketball-specific sources

&#x20; (Roberts 2019, Fort-Vanmeerhaeghe 2020, Hewett 2006)



\---



\## How to Work in This Repo



When given a task:



1\. Identify the entry point (usually dashboard.py)

2\. Trace how data flows into the relevant tab/module

3\. Identify root cause before suggesting changes

4\. Propose minimal fix first

5\. In sandbox, refactors are encouraged if they improve clarity or scalability



When editing:



\* Show exact file(s) to change

\* Show before → after code

\* Prefer modular, reusable structure

\* Keep UI and logic separated



When unsure:



\* Ask a clarifying question instead of guessing



\---



\## Common Failure Points



\* Tab not rendering due to incorrect import or function call

\* Streamlit tabs misaligned with function definitions

\* Mixing UI code and data logic

\* Incorrect data shape passed into visual components

\* Z-score calculations using wrong baseline reference



Always check these first when debugging.



\---



\## Context Files



\* WAIMS\_GLOBAL\_CONTEXT.md → long-term system thinking

\* WAIMS\_SESSION\_HANDOFF.md → short-term continuity



CLAUDE.md = execution rules (primary file)



\---



\## Session State



(Update at the end of every session)



Last completed:



\* \[ ]



Known issues:



\* \[ ]



Next priority:



\* \[ ]



\---



\## Compacting



When compacting, preserve:



\* current task

\* files inspected or changed

\* important commands

\* decisions already made

\* blockers or open questions



Do not preserve in detail:



\* long logs

\* repeated repo descriptions

\* unrelated exploration

\* rejected approaches unless still relevant



\---



