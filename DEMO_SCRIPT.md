# WAIMS-GM Demo Script

This is a repeatable 5-minute walkthrough for showing WAIMS-GM as a front-office decision-support product.

## Goal

Show that WAIMS-GM helps a GM, coach, or front-office staff member:

- evaluate a player in context
- understand the recommendation quickly
- compare two player files
- leave the app with a usable briefing artifact

## Demo Setup

Before the demo:

1. Run the FastAPI backend locally.
2. Run the Streamlit app locally.
3. Confirm the UI shows the `Sandbox` badge.
4. Generate a fresh sandbox bearer token with `scripts/get_token.py`.
5. Paste the token into the sidebar and click `Load briefing`.
6. Make sure at least two evaluations exist for compare mode.

## Recommended Story

Use the app as if a lower-resource basketball staff is trying to decide who should move to the top of the board.

Suggested frame:

"This is not a black-box AI GM. It is a structured basketball decision-support tool that turns player context, roster fit, risk, and value into a meeting-ready dossier."

## 5-Minute Walkthrough

### 1. Open the board

Show:

- the `Sandbox` runtime label
- the evaluation board
- filters for mode and recommendation

Say:

"The board gives us a quick decision queue. We can sort by score, recommendation, mode, or player name and stay focused on the current front-office question."

### 2. Open one player dossier

Select a player and show:

- recommendation
- overall score
- score cards
- executive memo
- decision lens
- Five Layer Diagnostic

Say:

"The point is not just to score the player. The point is to explain why the file is leaning toward a recommendation and where the pressure points are."

### 3. Highlight roster context

Call out:

- positional needs
- tension points
- cost tier
- health risk

Say:

"This is where a static scouting report becomes a front-office decision. The same player can read differently depending on roster need, cost, and timeline."

### 4. Compare two players

Choose a comparison player and show:

- comparison summary
- roster-need call
- verdict cards
- component comparison table

Say:

"This is the highest-value moment in the workflow. Instead of comparing two notes side by side manually, the tool gives a clear call on who better fits the current need."

### 5. Export

Download:

- dossier markdown
- comparison brief markdown

Say:

"The app is built to leave the meeting with something usable, not just a screen. That makes it easier for staff to carry the decision process forward."

## Suggested Demo Data Pattern

For the strongest compare moment:

- Player A: safer, higher-fit, lower-cost current contributor
- Player B: younger, higher-upside, less certain projection

This makes the compare view feel like a real front-office tradeoff instead of a fake no-brainer.

## What Good Looks Like

The demo is landing well if the viewer says one of these:

- "This saves time."
- "I can see how staff would use this before a meeting."
- "I like that the recommendation is explained."
- "The compare view is actually useful."

## Demo Checklist

- sandbox badge visible
- board loads without API errors
- dossier opens cleanly
- no clipped cards or text
- compare view loads
- export works
- delete works if needed
