from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx
import streamlit as st
from app.config import API_BASE_URL, IS_LIVE_ENV, WAIMS_DEMO_MODE, WAIMS_ENV_LABEL
from waims_gm.domain import Player, TeamContext
from waims_gm.demo_data import demo_payloads
from waims_gm.services import evaluate_single_player

try:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    WORD_EXPORT_AVAILABLE = True
    WORD_EXPORT_ERROR = ""
except Exception as e:
    WORD_EXPORT_AVAILABLE = False
    WORD_EXPORT_ERROR = str(e)

st.set_page_config(
    page_title="WAIMS-GM",
    page_icon=":basketball:",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=IBM+Plex+Mono:wght@400;500&family=Libre+Baskerville:wght@400;700&display=swap');

:root {
    --bg: #f5f0e6;
    --paper: #f8f3ea;
    --ink: #161616;
    --muted: #5f5a52;
    --gold: #9f7a2d;
    --line: rgba(22,22,22,0.12);
    --sidebar: #131313;
    --sidebar-ink: #e8dfd1;
    --card: rgba(255,255,255,0.52);
    --success: #345c3e;
    --danger: #8a3d32;
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        linear-gradient(to bottom, rgba(0,0,0,0.015), rgba(0,0,0,0.015)),
        repeating-linear-gradient(
            0deg,
            rgba(0,0,0,0.00) 0px,
            rgba(0,0,0,0.00) 22px,
            rgba(0,0,0,0.018) 23px
        ),
        var(--bg);
    color: var(--ink);
    font-family: "Libre Baskerville", serif;
}

[data-testid="stSidebar"] {
    background: var(--sidebar);
    color: var(--sidebar-ink);
    border-right: 1px solid rgba(255,255,255,0.06);
}

[data-testid="stSidebar"] * {
    color: var(--sidebar-ink);
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 1720px;
}

.waims-header {
    border-top: 3px solid var(--gold);
    border-bottom: 1px solid var(--line);
    padding: 0.6rem 0 1rem 0;
    margin-bottom: 1rem;
}

.waims-kicker {
    font-family: "IBM Plex Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    color: var(--muted);
    margin-bottom: 0.35rem;
}

.waims-title {
    font-family: "Playfair Display", serif;
    font-size: 2.2rem;
    line-height: 1.05;
    color: var(--ink);
    margin: 0;
}

.waims-subtitle {
    margin-top: 0.45rem;
    color: var(--muted);
    font-size: 0.98rem;
}

.waims-meta-row {
    margin-top: 0.7rem;
    display: flex;
    gap: 0.6rem;
    align-items: center;
    flex-wrap: wrap;
}

.env-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    border: 1px solid var(--line);
    padding: 0.18rem 0.65rem;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.env-badge-live {
    background: rgba(138, 61, 50, 0.10);
    color: var(--danger);
    border-color: rgba(138, 61, 50, 0.28);
}

.env-badge-sandbox {
    background: rgba(52, 92, 62, 0.10);
    color: var(--success);
    border-color: rgba(52, 92, 62, 0.28);
}

.metric-card {
    background: var(--card);
    border: 1px solid var(--line);
    border-top: 2px solid var(--gold);
    padding: 0.9rem 1rem;
    border-radius: 10px;
    min-height: 118px;
}

.metric-label {
    font-family: "IBM Plex Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: var(--muted);
}

.metric-value {
    font-family: "Playfair Display", serif;
    font-size: 1.85rem;
    margin-top: 0.2rem;
    color: var(--ink);
}

.metric-note {
    margin-top: 0.3rem;
    font-size: 0.85rem;
    color: var(--muted);
}

.section-title {
    font-family: "Playfair Display", serif;
    font-size: 1.28rem;
    margin: 1rem 0 0.5rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--line);
}

.section-kicker {
    font-family: "IBM Plex Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: var(--muted);
    margin-bottom: 0.25rem;
}

.intake-shell,
.detail-shell,
.board-card,
.soft-card {
    background: rgba(255,255,255,0.55);
    border: 1px solid var(--line);
    border-radius: 12px;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
}

.intake-shell,
.detail-shell {
    border-top: 2px solid var(--gold);
    padding: 1rem;
}

.intake-blurb {
    color: var(--muted);
    font-size: 0.93rem;
    margin-bottom: 0.8rem;
}

.board-card {
    border-left: 3px solid var(--gold);
    padding: 0.85rem 1rem;
    margin-bottom: 0.75rem;
}

.board-card-selected {
    background: rgba(255,255,255,0.76);
    border: 1px solid rgba(159,122,45,0.45);
    border-left: 4px solid var(--gold);
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

.board-head {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: baseline;
    flex-wrap: wrap;
}

.board-name {
    font-family: "Playfair Display", serif;
    font-size: 1.15rem;
    color: var(--ink);
    min-width: 0;
    overflow-wrap: anywhere;
}

.board-tag {
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--gold);
}

.board-meta {
    margin-top: 0.35rem;
    color: var(--muted);
    font-size: 0.9rem;
}

.board-note {
    margin-top: 0.45rem;
    color: var(--ink);
    font-size: 0.88rem;
    line-height: 1.45;
}

.player-title {
    font-family: "Playfair Display", serif;
    font-size: clamp(1.4rem, 2.8vw, 1.7rem);
    color: var(--ink);
    margin-bottom: 0.15rem;
    overflow-wrap: anywhere;
}

.player-meta {
    color: var(--muted);
    font-size: 0.95rem;
    overflow-wrap: anywhere;
}

.diagnostic-mini-card {
    border: 1px solid rgba(159,122,45,0.18);
    border-radius: 14px;
    padding: 0.5rem 0.65rem;
    background: rgba(255,255,255,0.72);
    min-width: 0;
}

.diagnostic-mini-label {
    font-family: "IBM Plex Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.62rem;
    color: var(--muted);
    margin-bottom: 0.18rem;
}

.diagnostic-mini-grade {
    font-family: "Playfair Display", serif;
    font-size: 1.1rem;
    line-height: 1;
    color: var(--ink);
}

.diagnostic-row-head {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin-bottom: 0.35rem;
}

.diagnostic-row-grade {
    font-family: "Playfair Display", serif;
    font-size: 1.35rem;
    line-height: 1;
    color: var(--gold);
    min-width: 1.2rem;
}

.rule {
    border-top: 1px solid var(--line);
    margin: 0.95rem 0 1rem 0;
}

.soft-card {
    padding: 0.9rem 1rem;
    height: 100%;
    overflow: hidden;
}

.mini-label {
    font-family: "IBM Plex Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.7rem;
    color: var(--muted);
    margin-bottom: 0.35rem;
}

.memo-text {
    color: var(--ink);
    line-height: 1.6;
    font-size: 0.97rem;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.subtle-list {
    margin: 0.25rem 0 0 0;
    padding-left: 1.1rem;
}

.subtle-list li {
    margin-bottom: 0.32rem;
    color: var(--ink);
}

.filter-note {
    color: var(--muted);
    font-size: 0.84rem;
}

.action-draft { color: var(--success); }
.action-sign { color: var(--gold); }
.action-pass { color: var(--danger); }

.score-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
    gap: 0.75rem;
    margin-bottom: 0.85rem;
    align-items: stretch;
}

.profile-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 0.75rem;
}

.profile-card {
    background: rgba(255,255,255,0.50);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
    min-height: 108px;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
}

.profile-label {
    color: var(--muted);
    font-size: 0.95rem;
    margin-bottom: 0.35rem;
    overflow-wrap: anywhere;
    word-break: break-word;
}

.profile-value {
    font-family: "Playfair Display", serif;
    font-size: clamp(1.9rem, 3.4vw, 3rem);
    line-height: 1.02;
    color: var(--ink);
    overflow-wrap: anywhere;
    word-break: break-word;
}

.score-card {
    background: rgba(255,255,255,0.50);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.8rem 0.9rem;
    min-height: 108px;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
}

.score-card-wide {
    grid-column: 1 / -1;
}

.score-label {
    font-size: 0.95rem;
    color: var(--muted);
    margin-bottom: 0.35rem;
}

.score-value {
    font-family: "Playfair Display", serif;
    font-size: clamp(1.65rem, 3.1vw, 2.35rem);
    line-height: 1.05;
    color: var(--ink);
    white-space: normal;
    overflow-wrap: anywhere;
    word-break: break-word;
}

textarea {
    min-height: 110px !important;
}

.stButton > button {
    border-radius: 8px;
}

div[data-testid="stMetric"] {
    border: 1px solid var(--line);
    border-radius: 10px;
    background: rgba(255,255,255,0.42);
    padding: 0.45rem 0.7rem;
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
    overflow: hidden;
}

div[data-testid="stMetricLabel"] {
    overflow-wrap: anywhere;
    word-break: break-word;
    min-width: 0;
}

div[data-testid="stMetricValue"] {
    font-size: clamp(1.6rem, 3vw, 2.35rem);
    line-height: 1.05;
    overflow-wrap: anywhere;
    word-break: break-word;
    white-space: normal;
    min-width: 0;
}

div[data-testid="stMetricLabel"] > div,
div[data-testid="stMetricValue"] > div {
    overflow-wrap: anywhere;
    word-break: break-word;
    white-space: normal;
}

[data-testid="column"] {
    min-width: 0;
}

hr {
    border: none;
    border-top: 1px solid var(--line);
    margin: 0.8rem 0 1rem 0;
}

.compare-grid {
    display: grid;
    gap: 0.55rem;
    min-width: 0;
}

.compare-row {
    display: grid;
    grid-template-columns: minmax(110px, 1.2fr) minmax(80px, 0.9fr) minmax(90px, 0.8fr) minmax(80px, 0.9fr);
    gap: 0.6rem;
    align-items: center;
    background: rgba(255,255,255,0.45);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    min-width: 0;
}

.compare-metric {
    font-family: "IBM Plex Mono", monospace;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: var(--muted);
}

.compare-score {
    font-family: "Playfair Display", serif;
    font-size: 1.18rem;
    color: var(--ink);
    overflow-wrap: anywhere;
}

.compare-advantage {
    text-align: center;
    color: var(--muted);
    font-size: 0.82rem;
    overflow-wrap: anywhere;
}

@media (max-width: 1200px) {
    .compare-row {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}
</style>
"""

MODE_LABELS = {
    "pro_wnba": "Pro / WNBA",
    "cbb_high_major": "CBB High-Major",
    "cbb_d2_low_resource": "CBB D2-3 NAIA Juco",
    "recruiting_only": "Recruiting Only",
}

DEFAULT_MODE = "cbb_d2_low_resource"

MODE_PLAYBOOKS: Dict[str, Dict[str, str]] = {
    "pro_wnba": {
        "headline": "Pro / WNBA acquisition lens",
        "primary_question": "Can this player solve a rotation problem without creating a value leak against pro-level cost and durability pressure?",
        "weight_note": "Impact drives the file first, then availability and role fit.",
        "create_note": "Use this mode when you care about immediate pro translation, contract pressure, and real rotation minutes.",
        "board_note": "Board view favors playable impact and cleaner short-window dependability over speculative upside.",
        "dossier_note": "Read the dossier as a front-office acquisition file with immediate rotation and cost discipline in mind.",
        "compare_note": "Compare mode should answer which player solves the current rotation question with the cleaner value profile.",
    },
    "cbb_high_major": {
        "headline": "High-major roster-building lens",
        "primary_question": "Can this player help a high-major program win quickly while still justifying portal cost and role usage?",
        "weight_note": "Impact and upside stay aggressive, with fit and value still important but not dominant.",
        "create_note": "Use this mode for portal leads, top-end adds, and players who must hold up against high-major role pressure.",
        "board_note": "Board view leans toward immediate game impact, usage scalability, and portal translation.",
        "dossier_note": "Read the dossier as a high-major add file: immediate usefulness matters, but a ceiling signal still moves the recommendation.",
        "compare_note": "Compare mode should tell you who is the better portal bet for your current high-major rotation and offense ecosystem.",
    },
    "cbb_d2_low_resource": {
        "headline": "D2 / NAIA / JUCO roster-build lens",
        "primary_question": "Can this player help us win soon without forcing our staff into a cost, risk, or roster-fit compromise?",
        "weight_note": "Value, fit, and availability matter more here than pure upside chasing.",
        "create_note": "Use this mode for D2, D3, NAIA, and Juco-style decisions where affordability, role clarity, and readiness matter.",
        "board_note": "Board view favors ready, affordable players who solve a live roster need without introducing avoidable instability.",
        "dossier_note": "Read the dossier as a small-staff roster file: the best target is often the one who helps now with the least operational drag.",
        "compare_note": "Compare mode should answer who gives the cleaner immediate return for the staff and roster you actually have.",
    },
    "recruiting_only": {
        "headline": "Long-horizon recruiting lens",
        "primary_question": "Is this prospect worth betting on because the long-term upside and age-adjusted runway justify the uncertainty?",
        "weight_note": "Upside and future value matter more than immediate impact or current minutes stability.",
        "create_note": "Use this mode for high-school, prep, or long-range recruiting decisions where runway matters more than instant rotation help.",
        "board_note": "Board view favors growth curve, positional need, and long-term upside more than near-term certainty.",
        "dossier_note": "Read the dossier as a projection file. The recommendation should reflect future leverage, not just current readiness.",
        "compare_note": "Compare mode should tell you which prospect is the better long-horizon bet for your program's future roster shape.",
    },
}

ACTION_LABELS = {
    "pro_wnba": {"draft": "Draft", "sign": "Sign", "pass": "Pass"},
    "cbb_high_major": {"draft": "Priority Target", "sign": "Take/Add", "pass": "Pass"},
    "cbb_d2_low_resource": {"draft": "Priority Target", "sign": "Fit Add", "pass": "Pass"},
    "recruiting_only": {"draft": "High Priority", "sign": "Monitor", "pass": "Pass"},
}

COMPONENT_LABELS = {
    "fit": "Fit",
    "impact": "Impact",
    "upside": "Upside",
    "availability": "Availability",
    "value": "Value",
}

CSV_IMPORT_COLUMNS = [
    "display_name",
    "player_id",
    "player_name",
    "position",
    "age",
    "offense_rating",
    "defense_rating",
    "shooting_rating",
    "playmaking_rating",
    "rebounding_rating",
    "health_risk",
    "upside",
    "minutes_stability",
    "expected_cost_tier",
    "team_id",
    "timeline",
    "need_g",
    "need_f",
    "need_c",
    "cap_flexibility",
    "risk_tolerance",
    "summary_note",
    "strengths",
    "concerns",
    "mode",
]

CSV_REQUIRED_COLUMNS = [
    "player_id",
    "player_name",
    "position",
    "age",
    "offense_rating",
    "defense_rating",
    "shooting_rating",
    "playmaking_rating",
    "rebounding_rating",
    "health_risk",
    "upside",
    "minutes_stability",
    "expected_cost_tier",
    "team_id",
    "timeline",
    "need_g",
    "need_f",
    "need_c",
    "cap_flexibility",
    "risk_tolerance",
]

PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "pro_wnba": {
        "3-and-D Wing": {
            "position": "F",
            "age": 24,
            "offense_rating": 72.0,
            "defense_rating": 82.0,
            "shooting_rating": 78.0,
            "playmaking_rating": 58.0,
            "rebounding_rating": 68.0,
            "health_risk": 0.20,
            "upside": 0.70,
            "minutes_stability": 0.78,
            "expected_cost_tier": 2,
            "need_g": 0.40,
            "need_f": 0.85,
            "need_c": 0.35,
            "summary_note": "Reliable wing target who fits a low-maintenance rotation role.",
            "strengths": "Defends multiple positions\nReliable catch-and-shoot spacing\nStable role acceptance",
            "concerns": "Limited self-creation\nMay be capped as a secondary piece",
        },
        "Second Unit Pace Guard": {
            "position": "G",
            "age": 26,
            "offense_rating": 75.0,
            "defense_rating": 61.0,
            "shooting_rating": 74.0,
            "playmaking_rating": 77.0,
            "rebounding_rating": 34.0,
            "health_risk": 0.18,
            "upside": 0.58,
            "minutes_stability": 0.74,
            "expected_cost_tier": 2,
            "need_g": 0.72,
            "need_f": 0.24,
            "need_c": 0.16,
            "summary_note": "Bench guard target who can stabilize second-unit offense without premium acquisition cost.",
            "strengths": "Pick-and-roll command\nSecond-unit shot creation\nTempo control",
            "concerns": "Size pressure on defense\nLess upside than younger guard bets",
        },
    },
    "cbb_high_major": {
        "Portal Lead Guard": {
            "position": "G",
            "age": 21,
            "offense_rating": 80.0,
            "defense_rating": 68.0,
            "shooting_rating": 76.0,
            "playmaking_rating": 84.0,
            "rebounding_rating": 46.0,
            "health_risk": 0.16,
            "upside": 0.76,
            "minutes_stability": 0.79,
            "expected_cost_tier": 3,
            "need_g": 0.85,
            "need_f": 0.45,
            "need_c": 0.20,
            "summary_note": "High-major portal guard with immediate usage and ball-screen value.",
            "strengths": "Creation\nDecision-making\nPull-up threat\nLate-clock offense",
            "concerns": "Defensive translation\nPrice sensitivity\nBall-dominant profile",
        },
        "Portal Two-Way Wing": {
            "position": "F",
            "age": 22,
            "offense_rating": 76.0,
            "defense_rating": 79.0,
            "shooting_rating": 77.0,
            "playmaking_rating": 61.0,
            "rebounding_rating": 63.0,
            "health_risk": 0.13,
            "upside": 0.73,
            "minutes_stability": 0.80,
            "expected_cost_tier": 3,
            "need_g": 0.35,
            "need_f": 0.84,
            "need_c": 0.22,
            "summary_note": "Portal wing with high-major defensive portability and enough shooting to hold a real role.",
            "strengths": "Positional defense\nCatch-and-shoot value\nRole flexibility",
            "concerns": "May not carry primary creation\nPortal market could drive price",
        },
    },
    "cbb_d2_low_resource": {
        "D2 Two-Way Wing": {
            "position": "F",
            "age": 20,
            "offense_rating": 71.0,
            "defense_rating": 77.0,
            "shooting_rating": 74.0,
            "playmaking_rating": 55.0,
            "rebounding_rating": 67.0,
            "health_risk": 0.15,
            "upside": 0.72,
            "minutes_stability": 0.81,
            "expected_cost_tier": 1,
            "need_g": 0.35,
            "need_f": 0.82,
            "need_c": 0.34,
            "summary_note": "Affordable two-way wing who can help a smaller staff win quickly.",
            "strengths": "Role clarity\nDefensive versatility\nShooting floor\nStrong budget fit",
            "concerns": "Creation ceiling\nMay need usage protection",
        },
        "Ready Guard Value Add": {
            "position": "G",
            "age": 22,
            "offense_rating": 73.0,
            "defense_rating": 74.0,
            "shooting_rating": 70.0,
            "playmaking_rating": 72.0,
            "rebounding_rating": 38.0,
            "health_risk": 0.11,
            "upside": 0.66,
            "minutes_stability": 0.86,
            "expected_cost_tier": 1,
            "need_g": 0.86,
            "need_f": 0.34,
            "need_c": 0.20,
            "summary_note": "Ready-made backcourt add who gives a smaller staff immediate competence and cheap minutes.",
            "strengths": "Decision security\nRole readiness\nBudget-friendly fit",
            "concerns": "Lower long-term ceiling\nDoes not solve frontcourt size",
        },
    },
    "recruiting_only": {
        "High-Upside Combo Guard": {
            "position": "G",
            "age": 18,
            "offense_rating": 73.0,
            "defense_rating": 63.0,
            "shooting_rating": 75.0,
            "playmaking_rating": 71.0,
            "rebounding_rating": 39.0,
            "health_risk": 0.12,
            "upside": 0.84,
            "minutes_stability": 0.60,
            "expected_cost_tier": 2,
            "need_g": 0.75,
            "need_f": 0.30,
            "need_c": 0.15,
            "summary_note": "Developmental guard with real long-term upside.",
            "strengths": "Shot-making\nHandle creativity\nGrowth curve",
            "concerns": "Physical maturity\nDecision stability\nDefensive readiness",
        },
        "Long Wing Upside Bet": {
            "position": "F",
            "age": 17,
            "offense_rating": 67.0,
            "defense_rating": 64.0,
            "shooting_rating": 71.0,
            "playmaking_rating": 56.0,
            "rebounding_rating": 61.0,
            "health_risk": 0.09,
            "upside": 0.89,
            "minutes_stability": 0.52,
            "expected_cost_tier": 2,
            "need_g": 0.28,
            "need_f": 0.81,
            "need_c": 0.26,
            "summary_note": "Length-and-skill wing bet with long-term lineup versatility if the physical development comes.",
            "strengths": "Frame upside\nProjectable jumper\nTwo-way runway",
            "concerns": "Needs strength\nCurrent impact is limited",
        },
    },
}


def inject_css() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def api_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local_score_detail_from_payload(
    payload: Dict[str, Any],
    evaluation_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    player_dict = dict(payload.get("player", {}) or {})
    ctx_dict = dict(payload.get("ctx", {}) or {})
    mode = payload.get("mode") or "pro_wnba"
    ctx_with_meta = ctx_dict | {"gm_id": "demo-local", "mode": mode}

    player = Player(**player_dict)
    ctx = TeamContext(**ctx_with_meta)
    scorecard = evaluate_single_player(player, ctx)

    return {
        "id": evaluation_id or f"demo-{uuid4().hex[:8]}",
        "gm_id": "demo-local",
        "team_id": ctx_dict.get("team_id"),
        "overall_score": scorecard.overall_score,
        "components": scorecard.components,
        "assumptions": scorecard.assumptions,
        "tension_points": scorecard.tension_points,
        "recommended_action": scorecard.recommended_action,
        "player": player_dict,
        "ctx": ctx_dict,
        "created_at": created_at or _now_iso(),
        "summary_note": payload.get("summary_note"),
        "strengths": payload.get("strengths"),
        "concerns": payload.get("concerns"),
        "mode": mode,
        "display_name": payload.get("display_name"),
    }


def _default_demo_details() -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for index, payload in enumerate(demo_payloads()):
        details.append(
            _local_score_detail_from_payload(
                payload,
                evaluation_id=f"demo-local-{index + 1}",
                created_at=_now_iso(),
            )
        )
    return details


def ensure_local_demo_state() -> None:
    if "local_demo_details" not in st.session_state:
        st.session_state["local_demo_details"] = _default_demo_details()


def _local_demo_details() -> List[Dict[str, Any]]:
    ensure_local_demo_state()
    return list(st.session_state["local_demo_details"])


def _save_local_demo_details(details: List[Dict[str, Any]]) -> None:
    st.session_state["local_demo_details"] = details


def get_evaluations(token: str) -> List[Dict[str, Any]]:
    if WAIMS_DEMO_MODE:
        return [
            {
                "id": row["id"],
                "gm_id": row["gm_id"],
                "team_id": row.get("team_id"),
                "overall_score": row["overall_score"],
                "recommended_action": row["recommended_action"],
                "created_at": row.get("created_at"),
                "player": row.get("player", {}),
                "summary_note": row.get("summary_note"),
                "mode": row.get("mode"),
            }
            for row in _local_demo_details()
        ]
    with httpx.Client(timeout=20) as client:
        r = client.get(f"{API_BASE_URL}/evaluations", headers=api_headers(token))
        r.raise_for_status()
        return r.json()


def get_evaluation_detail(token: str, evaluation_id: str) -> Dict[str, Any]:
    if WAIMS_DEMO_MODE:
        for row in _local_demo_details():
            if row["id"] == evaluation_id:
                return row
        raise KeyError(f"No local demo evaluation found for id {evaluation_id}")
    with httpx.Client(timeout=20) as client:
        r = client.get(
            f"{API_BASE_URL}/evaluations/{evaluation_id}",
            headers=api_headers(token),
        )
        r.raise_for_status()
        return r.json()


def create_evaluation(token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if WAIMS_DEMO_MODE:
        details = _local_demo_details()
        new_detail = _local_score_detail_from_payload(payload)
        details.insert(0, new_detail)
        _save_local_demo_details(details)
        return {
            "evaluation_id": new_detail["id"],
            "overall_score": new_detail["overall_score"],
            "components": new_detail["components"],
            "assumptions": new_detail["assumptions"],
            "tension_points": new_detail["tension_points"],
            "recommended_action": new_detail["recommended_action"],
            "player": new_detail["player"],
            "summary_note": new_detail.get("summary_note"),
            "strengths": new_detail.get("strengths"),
            "concerns": new_detail.get("concerns"),
            "mode": new_detail.get("mode"),
        }
    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{API_BASE_URL}/evaluate-and-save",
            headers=api_headers(token),
            json=payload,
        )
        r.raise_for_status()
        return r.json()


def delete_evaluation(token: str, evaluation_id: str) -> Dict[str, Any]:
    if WAIMS_DEMO_MODE:
        details = [row for row in _local_demo_details() if row["id"] != evaluation_id]
        _save_local_demo_details(details)
        return {"ok": True, "deleted_id": evaluation_id}
    with httpx.Client(timeout=20) as client:
        r = client.delete(
            f"{API_BASE_URL}/evaluations/{evaluation_id}",
            headers=api_headers(token),
        )
        r.raise_for_status()
        return r.json()


def format_score(value: Optional[float]) -> str:
    return "—" if value is None else f"{value:.2f}"


def format_dt(value: Optional[str]) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y • %I:%M %p")
    except Exception:
        return value


def clean_action(action: Optional[str], mode: Optional[str]) -> str:
    raw = (action or "").lower()
    mode = mode or "pro_wnba"
    return ACTION_LABELS.get(mode, ACTION_LABELS["pro_wnba"]).get(raw, raw.title() or "—")


def action_class(action: Optional[str]) -> str:
    action = (action or "").lower()
    if action == "draft":
        return "action-draft"
    if action == "sign":
        return "action-sign"
    if action == "pass":
        return "action-pass"
    return ""


def render_header() -> None:
    env_class = "env-badge-live" if IS_LIVE_ENV else "env-badge-sandbox"
    runtime_label = "Local Demo Mode" if WAIMS_DEMO_MODE else f"API {API_BASE_URL}"
    st.markdown(
        f"""
        <div class="waims-header">
            <div class="waims-kicker">Front Office Briefing Terminal</div>
            <h1 class="waims-title">WAIMS-GM Morning Brief</h1>
            <div class="waims-subtitle">
                Executive review layer for player evaluation, fit, risk, action, and scouting rationale.
            </div>
            <div class="waims-meta-row">
                <div class="env-badge {env_class}">{WAIMS_ENV_LABEL}</div>
                <div class="waims-kicker" style="margin-bottom:0;">{runtime_label}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_mode_playbook(mode: str) -> Dict[str, str]:
    return MODE_PLAYBOOKS.get(mode or DEFAULT_MODE, MODE_PLAYBOOKS[DEFAULT_MODE])


def render_mode_focus_banner(mode: str, surface: str, show_label: bool = True) -> None:
    mode = mode or DEFAULT_MODE
    playbook = get_mode_playbook(mode)
    notes = {
        "create": playbook["create_note"],
        "board": playbook["board_note"],
        "dossier": playbook["dossier_note"],
        "compare": playbook["compare_note"],
    }
    surface_label = {
        "create": "Mode Setup",
        "board": "Mode Focus",
        "dossier": "Dossier Lens",
        "compare": "Compare Lens",
    }
    if show_label:
        st.markdown(
            f'<div class="section-kicker" style="margin-top:0.2rem;">{surface_label.get(surface, "Mode Focus")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f"""
        <div class="soft-card" style="margin-bottom:0.85rem;">
            <div class="mini-label">{MODE_LABELS.get(mode, mode)}</div>
            <div class="board-name" style="font-size:1.05rem;">{playbook['headline']}</div>
            <div class="memo-text" style="margin-top:0.45rem;">
                <strong>Primary question:</strong> {playbook['primary_question']}
                <br/>
                <strong>Weighting bias:</strong> {playbook['weight_note']}
                <br/>
                {notes.get(surface, playbook['dossier_note'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summarize_context(ctx: Dict[str, Any]) -> str:
    return (
        f"Team {ctx.get('team_id', '—')} operating in a {ctx.get('timeline', '—')} window, "
        f"with cap flexibility {ctx.get('cap_flexibility', '—')} and risk tolerance {ctx.get('risk_tolerance', '—')}."
    )


def build_dossier_takeaways(detail: Dict[str, Any]) -> List[str]:
    detail = normalize_detail_for_display(detail)
    player = detail.get("player", {}) or {}
    ctx = detail.get("ctx", {}) or {}
    mode = detail.get("mode") or "pro_wnba"
    components = detail.get("components", {}) or {}
    component_scores = [(label, _component_number(components, key) or 0.0) for key, label in COMPONENT_LABELS.items()]
    component_scores.sort(key=lambda item: item[1], reverse=True)
    strongest_label, strongest_value = component_scores[0]

    needs = ctx.get("needs_by_position", {}) or {}
    pos = player.get("position", "—")
    need_value = needs.get(pos)
    need_line = (
        f"{pos} is a live roster-need position at {need_value:.2f}, which supports the current recommendation."
        if need_value is not None
        else "Roster-need data is limited, so fit should be validated against live board priorities."
    )

    tension_points = detail.get("tension_points", []) or []
    risk_line = tension_points[0] if tension_points else "No major tension points are currently flagged in this file."

    overall_score = format_score(detail.get("overall_score"))
    second_label, second_value = component_scores[1]
    playbook = get_mode_playbook(mode)

    return [
        f"Overall score: {overall_score}. Recommendation: {clean_action(detail.get('recommended_action'), mode)}.",
        f"Top components: {strongest_label} {format_score(strongest_value)} and {second_label} {format_score(second_value)}.",
        f"Mode lens: {playbook['weight_note']}",
        f"Roster / risk view: {need_line} Primary watch item: {risk_line}",
    ]


def build_executive_brief_cards(detail: Dict[str, Any]) -> List[Dict[str, str]]:
    detail = normalize_detail_for_display(detail)
    player = detail.get("player", {}) or {}
    ctx = detail.get("ctx", {}) or {}
    mode = detail.get("mode") or DEFAULT_MODE
    components = detail.get("components", {}) or {}
    component_scores = [
        (label, _component_number(components, key) or 0.0)
        for key, label in COMPONENT_LABELS.items()
    ]
    component_scores.sort(key=lambda item: item[1], reverse=True)
    strongest_label, strongest_value = component_scores[0]
    second_label, second_value = component_scores[1]

    needs = ctx.get("needs_by_position", {}) or {}
    pos = player.get("position", "—")
    need_value = needs.get(pos)
    tension_points = detail.get("tension_points", []) or []
    primary_watch = tension_points[0] if tension_points else "No major tension points are currently flagged in this file."

    why_now = (
        f"{clean_action(detail.get('recommended_action'), mode)} at {format_score(detail.get('overall_score'))}. "
        f"{strongest_label} ({format_score(strongest_value)}) and {second_label} ({format_score(second_value)}) are driving the file."
    )
    why_not = primary_watch
    decision_driver = (
        f"{pos} need is {need_value:.2f}. {get_mode_playbook(mode)['weight_note']}"
        if need_value is not None
        else get_mode_playbook(mode)["weight_note"]
    )

    return [
        {"title": "Why Now", "winner": clean_action(detail.get("recommended_action"), mode), "note": why_now},
        {"title": "Why Not", "winner": "Primary Watch Item", "note": why_not},
        {"title": "Decision Drivers", "winner": MODE_LABELS.get(mode, mode), "note": decision_driver},
    ]


def render_diagnostic_strip(detail: Dict[str, Any]) -> None:
    rows = compute_five_layer_diagnostic(detail)
    short_labels = {
        "Layer 1 — Scoring Profile": "Scoring",
        "Layer 2 — Creation Profile": "Creation",
        "Layer 3 — Defensive Translation": "Defense",
        "Layer 4 — Availability / Stability": "Stability",
        "Layer 5 — Value / Roster Fit": "Value / Fit",
    }
    st.markdown(
        '<div class="section-kicker" style="margin-top:0.55rem; margin-bottom:0.3rem;">Diagnostic Snapshot</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(rows), gap="small")
    for col, row in zip(cols, rows):
        with col:
            st.markdown(
                f"""
                <div class="diagnostic-mini-card">
                    <div class="diagnostic-mini-label">{short_labels.get(row['layer'], row['layer'])}</div>
                    <div class="diagnostic-mini-grade">{row['grade']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def build_memo(detail: Dict[str, Any]) -> str:
    player = detail.get("player", {}) or {}
    ctx = detail.get("ctx", {}) or {}
    summary_note = detail.get("summary_note") or ""
    base = (
        f"{player.get('name', 'This player')} profiles as a {player.get('position', '—')} target with an overall "
        f"score of {format_score(detail.get('overall_score'))}. The current recommendation is "
        f"{clean_action(detail.get('recommended_action'), detail.get('mode'))}. Age ({player.get('age', '—')}) and expected cost tier "
        f"({player.get('expected_cost_tier', '—')}) frame the acquisition lens, while the evaluation context points "
        f"toward {ctx.get('timeline', 'a flexible')} team-building priorities rather than a purely static rating interpretation."
    )
    if summary_note:
        base += f" Analyst note: {summary_note}"
    return base


def prepare_evaluations(
    evaluations: List[Dict[str, Any]],
    action_filter: str,
    hide_placeholder: bool,
    mode_filter: str,
) -> List[Dict[str, Any]]:
    rows = list(evaluations)
    if hide_placeholder:
        rows = [
            r for r in rows
            if (r.get("player", {}) or {}).get("name", "").strip().lower() not in {"string", ""}
        ]
    if action_filter != "All":
        rows = [r for r in rows if (r.get("recommended_action") or "").lower() == action_filter.lower()]
    if mode_filter != "All":
        rows = [r for r in rows if (r.get("mode") or "pro_wnba") == mode_filter]
    return rows


def sort_evaluations(rows: List[Dict[str, Any]], sort_by: str, descending: bool) -> List[Dict[str, Any]]:
    def key_fn(row: Dict[str, Any]):
        if sort_by == "Score":
            return float(row.get("overall_score") or 0)
        if sort_by == "Recommendation":
            return str(row.get("recommended_action") or "")
        if sort_by == "Mode":
            return str(row.get("mode") or "")
        if sort_by == "Player Name":
            return str((row.get("player") or {}).get("name") or "")
        return str(row.get("created_at") or "")
    return sorted(rows, key=key_fn, reverse=descending)


def render_summary_cards(evaluations: List[Dict[str, Any]]) -> None:
    total = len(evaluations)
    draft_count = sum(1 for e in evaluations if e.get("recommended_action") == "draft")
    sign_count = sum(1 for e in evaluations if e.get("recommended_action") == "sign")
    avg_score = (
        sum(float(e.get("overall_score", 0)) for e in evaluations) / total if total else 0
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-label">Saved Evaluations</div><div class="metric-value">{total}</div><div class="metric-note">Current briefing inventory</div></div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-label">Average Score</div><div class="metric-value">{avg_score:.2f}</div><div class="metric-note">Across filtered evaluations</div></div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""<div class="metric-card"><div class="metric-label">Action Mix</div><div class="metric-value">{draft_count} / {sign_count}</div><div class="metric-note">Top-end / middle-band recommendations</div></div>""",
            unsafe_allow_html=True,
        )


def render_empty_board_state() -> None:
    st.markdown(
        """
        <div class="soft-card" style="margin-top:0.85rem;">
            <div class="mini-label">Board Status</div>
            <div class="board-name" style="font-size:1.05rem;">No saved evaluations match the current view.</div>
            <div class="memo-text" style="margin-top:0.45rem;">
                Start by creating a new evaluation on the left, clear the active filters, or seed repeatable demo files with
                <code>scripts/seed_demo_data.py</code>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_decision_board(evaluations: List[Dict[str, Any]]) -> Optional[str]:
    st.markdown('<div class="section-kicker">Priority Queue</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Recent Evaluation Board</div>', unsafe_allow_html=True)

    if not evaluations:
        render_empty_board_state()
        return None

    existing_ids = {row["id"] for row in evaluations}
    selected_id = st.session_state.get("selected_evaluation_id")
    if selected_id not in existing_ids:
        selected_id = evaluations[0]["id"]
        st.session_state["selected_evaluation_id"] = selected_id

    for item in evaluations[:12]:
        player = item.get("player", {}) or {}
        note = item.get("summary_note") or ""
        selected = item["id"] == selected_id
        extra_class = " board-card-selected" if selected else ""
        mode = item.get("mode") or "pro_wnba"

        st.markdown(
            f"""
            <div class="board-card{extra_class}">
                <div class="board-head">
                    <div class="board-name">{player.get("name", "Unknown Player")}</div>
                    <div class="board-tag {action_class(item.get("recommended_action"))}">{clean_action(item.get("recommended_action"), mode)}</div>
                </div>
                <div class="board-meta">
                    {MODE_LABELS.get(mode, mode)} &nbsp;|&nbsp; {player.get("position", "—")}
                    &nbsp;|&nbsp; Score {format_score(item.get("overall_score"))}
                    &nbsp;|&nbsp; {format_dt(item.get("created_at"))}
                </div>
                {"<div class='board-note'>" + note + "</div>" if note else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Selected" if selected else f"Open {player.get('name', 'Player')}", key=f"open_{item['id']}", disabled=selected):
            st.session_state["selected_evaluation_id"] = item["id"]
            st.rerun()

    return st.session_state.get("selected_evaluation_id")


def render_bullets(text_block: Optional[str], fallback: str) -> str:
    if not text_block or not text_block.strip():
        return f"<li>{fallback}</li>"
    lines = [line.strip("•- ").strip() for line in text_block.splitlines() if line.strip()]
    if not lines:
        return f"<li>{fallback}</li>"
    return "".join(f"<li>{line}</li>" for line in lines)


def text_block_lines(text_block: Optional[str], fallback: Optional[str] = None) -> List[str]:
    lines = [line.strip("•- ").strip() for line in (text_block or "").splitlines() if line.strip()]
    if lines:
        return lines
    return [fallback] if fallback else []


def normalize_detail_for_display(detail: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(detail)
    raw_components = dict(normalized.get("components") or {})
    components: Dict[str, Optional[float]] = {}

    for key in COMPONENT_LABELS:
        value = raw_components.get(key)
        try:
            components[key] = None if value in (None, "") else float(value)
        except (TypeError, ValueError):
            components[key] = None

    legacy_availability = raw_components.get("risk_inverse")
    try:
        if components["availability"] is None and legacy_availability not in (None, ""):
            legacy_value = float(legacy_availability)
            components["availability"] = legacy_value * 100 if legacy_value <= 1 else legacy_value
    except (TypeError, ValueError):
        pass

    if any(value is None for value in components.values()):
        player_payload = normalized.get("player") or {}
        ctx_payload = dict(normalized.get("ctx") or {})

        if player_payload and ctx_payload:
            try:
                ctx_payload.setdefault("gm_id", str(normalized.get("gm_id") or "legacy-display"))
                ctx_payload.setdefault("mode", normalized.get("mode") or ctx_payload.get("mode") or "pro_wnba")
                rescored = evaluate_single_player(
                    Player(**player_payload),
                    TeamContext(**ctx_payload),
                )
                for key, value in rescored.components.items():
                    if components.get(key) is None:
                        components[key] = float(value)
            except Exception:
                pass

    normalized["components"] = {
        key: round(value, 2)
        for key, value in components.items()
        if value is not None
    }
    return normalized


def _component_number(components: Dict[str, Any], key: str) -> Optional[float]:
    value = components.get(key)
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def build_decision_lens(detail: Dict[str, Any]) -> str:
    normalized = normalize_detail_for_display(detail)
    components = normalized.get("components", {}) or {}
    mode = normalized.get("mode") or "pro_wnba"

    metric_blurbs = {
        "fit": "current roster fit",
        "impact": "immediate impact",
        "upside": "long-term upside",
        "availability": "near-term dependability",
        "value": "value-to-cost profile",
    }
    mode_lenses = {
        "pro_wnba": "win-now acquisition",
        "cbb_high_major": "high-major translation",
        "cbb_d2_low_resource": "small-staff roster",
        "recruiting_only": "long-horizon recruiting",
    }

    ranked = [
        (key, value)
        for key in COMPONENT_LABELS
        if (value := _component_number(components, key)) is not None
    ]
    if not ranked:
        return "This file still needs more complete component data before a sharper acquisition lens can be stated."

    ranked.sort(key=lambda item: item[1], reverse=True)
    strongest_key, strongest_value = ranked[0]
    weakest_key, weakest_value = ranked[-1]
    recommendation = clean_action(normalized.get("recommended_action"), mode)

    return (
        f"This profile reads most strongly through a {mode_lenses.get(mode, 'basketball decision')} lens: "
        f"{metric_blurbs[strongest_key]} is the main reason the file carries a {recommendation} recommendation "
        f"({strongest_value:.1f}), while {metric_blurbs[weakest_key]} remains the cleanest pressure point "
        f"to monitor ({weakest_value:.1f})."
    )


def build_comparison_verdicts(left_detail: Dict[str, Any], right_detail: Dict[str, Any]) -> List[Dict[str, str]]:
    left_name = (left_detail.get("player") or {}).get("name", "Selected Player")
    right_name = (right_detail.get("player") or {}).get("name", "Comparison Player")
    left_components = left_detail.get("components", {}) or {}
    right_components = right_detail.get("components", {}) or {}
    mode = left_detail.get("mode") or right_detail.get("mode") or "pro_wnba"

    label_map = {
        "pro_wnba": "Best current roster target",
        "cbb_high_major": "Best high-major fit",
        "cbb_d2_low_resource": "Best current roster target",
        "recruiting_only": "Best long-range target",
    }
    verdict_specs = [
        (label_map.get(mode, "Best current roster target"), "fit", "fit"),
        ("Safer near-term bet", "availability", "availability"),
        ("Higher long-term upside", "upside", "upside"),
        ("Better value profile", "value", "value"),
    ]

    verdicts: List[Dict[str, str]] = []
    for title, key, blurb in verdict_specs:
        left_value = _component_number(left_components, key)
        right_value = _component_number(right_components, key)
        if left_value is None and right_value is None:
            continue

        if left_value is None:
            winner = right_name
            margin = None
        elif right_value is None:
            winner = left_name
            margin = None
        elif abs(left_value - right_value) < 0.01:
            winner = "Even"
            margin = 0.0
        elif left_value > right_value:
            winner = left_name
            margin = left_value - right_value
        else:
            winner = right_name
            margin = right_value - left_value

        if winner == "Even":
            note = f"Both players grade essentially even on {blurb}."
        elif margin is None:
            note = f"{winner} is the only file with usable {blurb} data in this comparison."
        else:
            note = f"{winner} leads {blurb} by {margin:.1f} points."

        verdicts.append({"title": title, "winner": winner, "note": note})

    return verdicts


def build_compare_decision_snapshot(left_detail: Dict[str, Any], right_detail: Dict[str, Any]) -> List[Dict[str, str]]:
    left_name = (left_detail.get("player") or {}).get("name", "Selected Player")
    right_name = (right_detail.get("player") or {}).get("name", "Comparison Player")
    mode = left_detail.get("mode") or right_detail.get("mode") or "pro_wnba"

    lane_weights = {
        "pro_wnba": {
            "win_now": {"fit": 0.34, "impact": 0.34, "availability": 0.22, "value": 0.07, "upside": 0.03},
            "asset": {"fit": 0.18, "impact": 0.18, "availability": 0.14, "value": 0.18, "upside": 0.32},
            "efficiency": {"fit": 0.22, "impact": 0.12, "availability": 0.16, "value": 0.40, "upside": 0.10},
        },
        "cbb_high_major": {
            "win_now": {"fit": 0.32, "impact": 0.31, "availability": 0.16, "value": 0.07, "upside": 0.14},
            "asset": {"fit": 0.20, "impact": 0.13, "availability": 0.10, "value": 0.17, "upside": 0.40},
            "efficiency": {"fit": 0.25, "impact": 0.10, "availability": 0.12, "value": 0.38, "upside": 0.15},
        },
        "cbb_d2_low_resource": {
            "win_now": {"fit": 0.32, "impact": 0.18, "availability": 0.22, "value": 0.22, "upside": 0.06},
            "asset": {"fit": 0.18, "impact": 0.08, "availability": 0.10, "value": 0.19, "upside": 0.45},
            "efficiency": {"fit": 0.26, "impact": 0.08, "availability": 0.16, "value": 0.42, "upside": 0.08},
        },
        "recruiting_only": {
            "win_now": {"fit": 0.22, "impact": 0.10, "availability": 0.10, "value": 0.12, "upside": 0.46},
            "asset": {"fit": 0.18, "impact": 0.06, "availability": 0.06, "value": 0.12, "upside": 0.58},
            "efficiency": {"fit": 0.21, "impact": 0.05, "availability": 0.08, "value": 0.28, "upside": 0.38},
        },
    }
    lane_meta = {
        "win_now": ("Best current rotation answer", "best matches the immediate roster problem"),
        "asset": ("Best long-term asset bet", "carries the strongest future-facing return profile"),
        "efficiency": ("Best value decision", "gives the cleanest return relative to cost and risk"),
    }
    weights_by_lane = lane_weights.get(mode, lane_weights["pro_wnba"])

    def lane_score(detail: Dict[str, Any], weights: Dict[str, float]) -> float:
        components = detail.get("components", {}) or {}
        return sum((_component_number(components, key) or 0.0) * weight for key, weight in weights.items())

    snapshot = []
    for lane, weights in weights_by_lane.items():
        left_score = lane_score(left_detail, weights)
        right_score = lane_score(right_detail, weights)
        title, rationale = lane_meta[lane]

        if abs(left_score - right_score) < 0.5:
            winner = "Even"
            note = f"Both files land nearly level here, so budget and staff conviction should break the tie."
        elif left_score > right_score:
            winner = left_name
            note = f"{left_name} {rationale} by {left_score - right_score:.1f} points."
        else:
            winner = right_name
            note = f"{right_name} {rationale} by {right_score - left_score:.1f} points."

        snapshot.append({"title": title, "winner": winner, "note": note})

    return snapshot


def build_roster_need_call(left_detail: Dict[str, Any], right_detail: Dict[str, Any]) -> Dict[str, str]:
    left_name = (left_detail.get("player") or {}).get("name", "Selected Player")
    right_name = (right_detail.get("player") or {}).get("name", "Comparison Player")
    left_player = left_detail.get("player", {}) or {}
    right_player = right_detail.get("player", {}) or {}
    ctx = left_detail.get("ctx") or right_detail.get("ctx") or {}
    mode = left_detail.get("mode") or right_detail.get("mode") or "pro_wnba"

    mode_titles = {
        "pro_wnba": "Roster Need Call",
        "cbb_high_major": "High-Major Need Call",
        "cbb_d2_low_resource": "Roster Need Call",
        "recruiting_only": "Recruiting Need Call",
    }
    mode_lenses = {
        "pro_wnba": "This lens leans toward fit, impact, and dependable availability.",
        "cbb_high_major": "This lens leans toward fit, impact, and high-major translation.",
        "cbb_d2_low_resource": "This lens leans toward fit, value, and near-term reliability.",
        "recruiting_only": "This lens leans toward upside, fit, and long-horizon value.",
    }
    compare_weights = {
        "pro_wnba": {"fit": 0.34, "impact": 0.30, "availability": 0.20, "value": 0.10, "upside": 0.06},
        "cbb_high_major": {"fit": 0.32, "impact": 0.28, "availability": 0.14, "value": 0.10, "upside": 0.16},
        "cbb_d2_low_resource": {"fit": 0.30, "impact": 0.12, "availability": 0.18, "value": 0.30, "upside": 0.10},
        "recruiting_only": {"fit": 0.22, "impact": 0.08, "availability": 0.05, "value": 0.15, "upside": 0.50},
    }
    weights = compare_weights.get(mode, compare_weights["pro_wnba"])
    needs = ctx.get("needs_by_position", {}) or {}

    def _position_need(player: Dict[str, Any]) -> float:
        try:
            return float(needs.get(player.get("position"), 0.5)) * 100
        except (TypeError, ValueError):
            return 50.0

    def _blended_score(detail: Dict[str, Any]) -> float:
        components = detail.get("components", {}) or {}
        component_score = sum(
            (_component_number(components, key) or 0.0) * weight
            for key, weight in weights.items()
        )
        return component_score * 0.78 + _position_need(detail.get("player", {}) or {}) * 0.22

    left_score = _blended_score(left_detail)
    right_score = _blended_score(right_detail)

    if abs(left_score - right_score) < 0.5:
        winner = "Even"
        margin_note = "The files land close enough that the tie should be broken by budget, staff preference, or live intel."
    elif left_score > right_score:
        winner = left_name
        margin_note = f"{left_name} fits the current need stack more cleanly by {left_score - right_score:.1f} points."
    else:
        winner = right_name
        margin_note = f"{right_name} fits the current need stack more cleanly by {right_score - left_score:.1f} points."

    primary_need = None
    if needs:
        try:
            primary_need = max(needs.items(), key=lambda item: float(item[1]))[0]
        except (TypeError, ValueError):
            primary_need = None

    left_pos = left_player.get("position", "—")
    right_pos = right_player.get("position", "—")
    need_note = (
        f"The sharpest current roster need is {primary_need}, with {left_name} profiled at {left_pos} and {right_name} at {right_pos}."
        if primary_need
        else f"{left_name} profiles at {left_pos} and {right_name} at {right_pos}, so the call is being made mostly on component shape rather than a strong positional need."
    )

    return {
        "title": mode_titles.get(mode, "Roster Need Call"),
        "winner": winner,
        "note": f"{margin_note} {need_note} {mode_lenses.get(mode, '')}".strip(),
    }


def compute_five_layer_diagnostic(detail: Dict[str, Any]) -> List[Dict[str, str]]:
    player = detail.get("player", {}) or {}
    offense = float(player.get("offense_rating", 0))
    defense = float(player.get("defense_rating", 0))
    shooting = float(player.get("shooting_rating", 0))
    playmaking = float(player.get("playmaking_rating", 0))
    rebounding = float(player.get("rebounding_rating", 0))
    health_risk = float(player.get("health_risk", 0))
    upside = float(player.get("upside", 0))
    minutes = float(player.get("minutes_stability", 0))
    cost = float(player.get("expected_cost_tier", 0))
    overall = float(detail.get("overall_score", 0))

    def grade(v: float) -> str:
        if v >= 80:
            return "A"
        if v >= 70:
            return "B"
        if v >= 60:
            return "C"
        return "D"

    scoring_val = (offense + shooting) / 2
    creation_val = (playmaking + offense) / 2
    defense_val = (defense + rebounding * 0.3) / 1.3
    availability_val = ((1 - health_risk) * 100 * 0.5) + (minutes * 100 * 0.5)
    value_fit_val = min(100, overall * 3.5 + (100 - cost * 10) * 0.25 + upside * 25)

    return [
        {"layer": "Layer 1 — Scoring Profile", "grade": grade(scoring_val), "note": f"Shooting/offense blend indicates a {grade(scoring_val)} scoring profile for current target context."},
        {"layer": "Layer 2 — Creation Profile", "grade": grade(creation_val), "note": f"Playmaking plus offensive creation suggest {'primary' if creation_val >= 75 else 'secondary'} initiator utility."},
        {"layer": "Layer 3 — Defensive Translation", "grade": grade(defense_val), "note": f"Defensive rating and support traits point to a {grade(defense_val)} defensive portability band."},
        {"layer": "Layer 4 — Availability / Stability", "grade": grade(availability_val), "note": f"Health risk and minutes stability combine into a {grade(availability_val)} dependability signal."},
        {"layer": "Layer 5 — Value / Roster Fit", "grade": grade(value_fit_val), "note": f"Overall score, cost tier, upside, and team context combine to a {grade(value_fit_val)} acquisition value fit."},
    ]


def compare_summary(left_detail: Dict[str, Any], right_detail: Dict[str, Any]) -> str:
    left_name = (left_detail.get("player") or {}).get("name", "Selected Player")
    right_name = (right_detail.get("player") or {}).get("name", "Comparison Player")
    left_score = float(left_detail.get("overall_score") or 0)
    right_score = float(right_detail.get("overall_score") or 0)

    if left_score > right_score:
        winner = left_name
        margin = left_score - right_score
    elif right_score > left_score:
        winner = right_name
        margin = right_score - left_score
    else:
        winner = "Neither player"
        margin = 0.0

    left_player = left_detail.get("player") or {}
    right_player = right_detail.get("player") or {}

    left_strength = max(
        [
            ("offense", float(left_player.get("offense_rating", 0))),
            ("defense", float(left_player.get("defense_rating", 0))),
            ("shooting", float(left_player.get("shooting_rating", 0))),
            ("playmaking", float(left_player.get("playmaking_rating", 0))),
            ("rebounding", float(left_player.get("rebounding_rating", 0))),
        ],
        key=lambda x: x[1],
    )[0]

    right_strength = max(
        [
            ("offense", float(right_player.get("offense_rating", 0))),
            ("defense", float(right_player.get("defense_rating", 0))),
            ("shooting", float(right_player.get("shooting_rating", 0))),
            ("playmaking", float(right_player.get("playmaking_rating", 0))),
            ("rebounding", float(right_player.get("rebounding_rating", 0))),
        ],
        key=lambda x: x[1],
    )[0]

    if winner == "Neither player":
        return (
            f"{left_name} and {right_name} are effectively level on overall score. "
            f"{left_name} leans most heavily on {left_strength}, while {right_name} leans most heavily on {right_strength}. "
            "The better choice depends on roster context, cost sensitivity, and role need."
        )

    return (
        f"{winner} grades better overall by {margin:.2f} points. "
        f"{left_name}'s strongest profile area is {left_strength}, while {right_name}'s strongest profile area is {right_strength}. "
        "The decision should now be framed through role fit, price discipline, and timeline rather than raw score alone."
    )


def render_score_cards(detail: Dict[str, Any], components: Dict[str, Any]) -> None:
    recommendation = clean_action(detail.get("recommended_action"), detail.get("mode"))

    def fmt(v: Any) -> str:
        if v in (None, "", "—"):
            return "—"
        try:
            return f"{float(v):.1f}"
        except Exception:
            return str(v)

    st.markdown(
        f"""
        <div class="score-grid">
            <div class="score-card">
                <div class="score-label">Fit</div>
                <div class="score-value">{fmt(components.get("fit"))}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Impact</div>
                <div class="score-value">{fmt(components.get("impact"))}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Upside</div>
                <div class="score-value">{fmt(components.get("upside"))}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Availability</div>
                <div class="score-value">{fmt(components.get("availability"))}</div>
            </div>
            <div class="score-card">
                <div class="score-label">Value</div>
                <div class="score-value">{fmt(components.get("value"))}</div>
            </div>
            <div class="score-card score-card-wide">
                <div class="score-label">Recommendation</div>
                <div class="score-value">{recommendation}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_cards(items: List[tuple[str, Any]], columns_per_row: int = 2) -> None:
    safe_columns = max(1, columns_per_row)
    for start in range(0, len(items), safe_columns):
        row = items[start : start + safe_columns]
        cols = st.columns(safe_columns, gap="small")
        for col, (label, value) in zip(cols, row):
            display = "—" if value in (None, "", "—") else value
            with col:
                st.markdown(
                    f"""
                    <div class="profile-card">
                        <div class="profile-label">{label}</div>
                        <div class="profile-value">{display}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_soft_card_grid(items: List[Dict[str, str]], columns_per_row: int = 2, top_margin: str = "0.85rem") -> None:
    safe_columns = max(1, columns_per_row)
    for start in range(0, len(items), safe_columns):
        row = items[start : start + safe_columns]
        cols = st.columns(safe_columns, gap="large")
        for col, item in zip(cols, row):
            with col:
                st.markdown(
                    f"""
                    <div class="soft-card" style="margin-top:{top_margin};">
                        <div class="mini-label">{item['title']}</div>
                        <div class="board-name" style="font-size:1rem;">{item['winner']}</div>
                        <div class="memo-text" style="margin-top:0.45rem;">{item['note']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def render_five_layer_diagnostic(detail: Dict[str, Any]) -> None:
    st.markdown('<div class="section-kicker" style="margin-top:1rem;">Diagnostic Layer</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Five Layer Diagnostic</div>', unsafe_allow_html=True)
    for row in compute_five_layer_diagnostic(detail):
        st.markdown(
            f"""
            <div class="soft-card" style="margin-bottom:0.75rem;">
                <div class="diagnostic-row-head">
                    <div class="diagnostic-row-grade">{row['grade']}</div>
                    <div class="mini-label" style="margin-bottom:0;">{row['layer']}</div>
                </div>
                <div class="memo-text" style="margin-top:0.45rem;">{row['note']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_detail(detail: Dict[str, Any], show_diagnostic: bool = True, show_heading: bool = True) -> None:
    detail = normalize_detail_for_display(detail)
    player = detail.get("player", {}) or {}
    ctx = detail.get("ctx", {}) or {}
    components = detail.get("components", {}) or {}
    assumptions = detail.get("assumptions", {}) or {}
    tension_points = detail.get("tension_points", []) or []
    mode = detail.get("mode") or "pro_wnba"

    if show_heading:
        st.markdown('<div class="section-kicker">Selected File</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Evaluation Dossier</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="detail-shell">
            <div class="board-head">
                <div>
                    <div class="player-title">{player.get("name", "Unknown Player")}</div>
                    <div class="player-meta">
                        {MODE_LABELS.get(mode, mode)} &nbsp;|&nbsp;
                        {player.get("position", "—")} &nbsp;|&nbsp;
                        Team {detail.get("team_id", "—")} &nbsp;|&nbsp;
                        Score {format_score(detail.get("overall_score"))} &nbsp;|&nbsp;
                        {format_dt(detail.get("created_at"))}
                    </div>
                </div>
                <div class="board-tag {action_class(detail.get("recommended_action"))}">{clean_action(detail.get("recommended_action"), mode)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_diagnostic_strip(detail)
    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

    render_soft_card_grid(build_executive_brief_cards(detail), columns_per_row=3, top_margin="0")
    takeaway_items = "".join(f"<li>{item}</li>" for item in build_dossier_takeaways(detail))
    st.markdown(
        f"""
        <div class="soft-card" style="margin-top:0.8rem; margin-bottom:0.9rem;">
            <div class="mini-label">Top Takeaways</div>
            <ul class="subtle-list">{takeaway_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([0.95, 1.2], gap="large")

    with top_left:
        render_profile_cards(
            [
                ("Age", player.get("age", "—")),
                ("Position", player.get("position", "—")),
                ("Cost Tier", player.get("expected_cost_tier", "—")),
                ("Health Risk", player.get("health_risk", "—")),
                ("Upside", player.get("upside", "—")),
                ("Minutes Stability", player.get("minutes_stability", "—")),
            ]
        )

        st.markdown(
            f"""
            <div class="soft-card" style="margin-top:0.85rem;">
                <div class="mini-label">Context Summary</div>
                <div class="memo-text">{summarize_context(ctx)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_right:
        st.markdown(
            f"""
            <div class="soft-card">
                <div class="mini-label">Executive Memo</div>
                <div class="memo-text">{build_memo(detail)}</div>
                <div class="rule"></div>
                <div class="mini-label">Decision Lens</div>
                <div class="memo-text">{build_decision_lens(detail)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    mid_left, mid_right = st.columns([0.95, 1.2], gap="large")

    with mid_left:
        render_score_cards(detail, components)

        assumption_items = "".join(
            [f"<li>{k.replace('_', ' ').title()}: {v}</li>" for k, v in assumptions.items()]
        ) or "<li>No assumptions recorded.</li>"

        st.markdown(
            f"""
            <div class="soft-card" style="margin-top:0.85rem;">
                <div class="mini-label">Assumptions</div>
                <ul class="subtle-list">{assumption_items}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with mid_right:
        needs = ctx.get("needs_by_position", {}) or {}
        needs_text = ", ".join(f"{k}: {v}" for k, v in needs.items()) if needs else "No positional needs recorded."
        tension_items = "".join([f"<li>{item}</li>" for item in tension_points]) or "<li>No major tension points flagged.</li>"

        st.markdown(
            f"""
            <div class="soft-card">
                <div class="mini-label">Positional Needs</div>
                <div class="memo-text">{needs_text}</div>
                <div class="rule"></div>
                <div class="mini-label">Tension Points</div>
                <ul class="subtle-list">{tension_items}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    bottom_left, bottom_right = st.columns([1, 1], gap="large")

    with bottom_left:
        st.markdown(
            f"""
            <div class="soft-card">
                <div class="mini-label">Strengths</div>
                <ul class="subtle-list">{render_bullets(detail.get("strengths"), "No strengths entered.")}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with bottom_right:
        st.markdown(
            f"""
            <div class="soft-card">
                <div class="mini-label">Concerns</div>
                <ul class="subtle-list">{render_bullets(detail.get("concerns"), "No concerns entered.")}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if show_diagnostic:
        render_five_layer_diagnostic(detail)


def render_compare_block(left_detail: Dict[str, Any], right_detail: Dict[str, Any]) -> None:
    left_detail = normalize_detail_for_display(left_detail)
    right_detail = normalize_detail_for_display(right_detail)

    st.markdown('<div class="section-kicker" style="margin-top:1rem;">Comparison Layer</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Side-by-Side Comparison</div>', unsafe_allow_html=True)

    left_name = (left_detail.get("player") or {}).get("name", "Selected Player")
    right_name = (right_detail.get("player") or {}).get("name", "Comparison Player")
    left_components = left_detail.get("components", {}) or {}
    right_components = right_detail.get("components", {}) or {}

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown(f"**{left_name}**")
        st.metric("Overall Score", format_score(left_detail.get("overall_score")))
        st.metric("Action", clean_action(left_detail.get("recommended_action"), left_detail.get("mode")))
        st.write(left_detail.get("summary_note") or "No summary note.")
    with c2:
        st.markdown(f"**{right_name}**")
        st.metric("Overall Score", format_score(right_detail.get("overall_score")))
        st.metric("Action", clean_action(right_detail.get("recommended_action"), right_detail.get("mode")))
        st.write(right_detail.get("summary_note") or "No summary note.")

    st.markdown(
        f"""
        <div class="soft-card" style="margin-top:0.85rem;">
            <div class="mini-label">Comparison Summary</div>
            <div class="memo-text">{compare_summary(left_detail, right_detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    roster_need_call = build_roster_need_call(left_detail, right_detail)
    st.markdown(
        f"""
        <div class="soft-card" style="margin-top:0.85rem;">
            <div class="mini-label">{roster_need_call['title']}</div>
            <div class="board-name" style="font-size:1.05rem;">{roster_need_call['winner']}</div>
            <div class="memo-text" style="margin-top:0.45rem;">{roster_need_call['note']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    decision_snapshot = build_compare_decision_snapshot(left_detail, right_detail)
    if decision_snapshot:
        render_soft_card_grid(decision_snapshot, columns_per_row=2)

    verdicts = build_comparison_verdicts(left_detail, right_detail)
    if verdicts:
        render_soft_card_grid(verdicts, columns_per_row=2)

    comparison_rows = []
    for key, label in COMPONENT_LABELS.items():
        left_value = left_components.get(key)
        right_value = right_components.get(key)

        if left_value is None and right_value is None:
            continue

        if left_value is None:
            edge = right_name
        elif right_value is None:
            edge = left_name
        elif abs(float(left_value) - float(right_value)) < 0.01:
            edge = "Even"
        else:
            edge = left_name if float(left_value) > float(right_value) else right_name

        comparison_rows.append(
            f"""
            <div class="compare-row">
                <div class="compare-metric">{label}</div>
                <div class="compare-score">{format_score(left_value)}</div>
                <div class="compare-advantage">{edge}</div>
                <div class="compare-score">{format_score(right_value)}</div>
            </div>
            """
        )

    if comparison_rows:
        st.markdown('<div class="section-kicker" style="margin-top:1rem;">Component Layer</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Component Comparison</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="compare-grid">
                {''.join(comparison_rows)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    notes_left, notes_right = st.columns(2, gap="large")
    with notes_left:
        st.markdown(
            f"""
            <div class="soft-card" style="margin-top:0.85rem;">
                <div class="mini-label">{left_name} Strengths</div>
                <ul class="subtle-list">{render_bullets(left_detail.get("strengths"), "No strengths entered.")}</ul>
                <div class="rule"></div>
                <div class="mini-label">{left_name} Concerns</div>
                <ul class="subtle-list">{render_bullets(left_detail.get("concerns"), "No concerns entered.")}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with notes_right:
        st.markdown(
            f"""
            <div class="soft-card" style="margin-top:0.85rem;">
                <div class="mini-label">{right_name} Strengths</div>
                <ul class="subtle-list">{render_bullets(right_detail.get("strengths"), "No strengths entered.")}</ul>
                <div class="rule"></div>
                <div class="mini-label">{right_name} Concerns</div>
                <ul class="subtle-list">{render_bullets(right_detail.get("concerns"), "No concerns entered.")}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_payload_from_form(
    display_name: str,
    player_id: str,
    player_name: str,
    position: str,
    age: int,
    offense_rating: float,
    defense_rating: float,
    shooting_rating: float,
    playmaking_rating: float,
    rebounding_rating: float,
    health_risk: float,
    upside: float,
    minutes_stability: float,
    expected_cost_tier: int,
    team_id: str,
    timeline: str,
    need_g: float,
    need_f: float,
    need_c: float,
    cap_flexibility: float,
    risk_tolerance: float,
    summary_note: str,
    strengths: str,
    concerns: str,
    mode: str,
) -> Dict[str, Any]:
    return {
        "player": {
            "id": player_id,
            "name": player_name,
            "position": position,
            "age": age,
            "offense_rating": offense_rating,
            "defense_rating": defense_rating,
            "shooting_rating": shooting_rating,
            "playmaking_rating": playmaking_rating,
            "rebounding_rating": rebounding_rating,
            "health_risk": health_risk,
            "upside": upside,
            "minutes_stability": minutes_stability,
            "expected_cost_tier": expected_cost_tier,
        },
        "ctx": {
            "team_id": team_id,
            "timeline": timeline,
            "needs_by_position": {"G": need_g, "F": need_f, "C": need_c},
            "cap_flexibility": cap_flexibility,
            "risk_tolerance": risk_tolerance,
        },
        "display_name": display_name,
        "summary_note": summary_note,
        "strengths": strengths,
        "concerns": concerns,
        "mode": mode,
    }


def _csv_cell(row: Dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def _csv_float(row: Dict[str, str], key: str, row_num: int) -> float:
    raw = _csv_cell(row, key)
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Row {row_num}: `{key}` must be a number.") from exc


def _csv_int(row: Dict[str, str], key: str, row_num: int) -> int:
    raw = _csv_cell(row, key)
    try:
        return int(float(raw))
    except ValueError as exc:
        raise ValueError(f"Row {row_num}: `{key}` must be a whole number.") from exc


def _payload_to_csv_row(payload: Dict[str, Any]) -> Dict[str, str]:
    player = payload.get("player", {}) or {}
    ctx = payload.get("ctx", {}) or {}
    needs = ctx.get("needs_by_position", {}) or {}
    return {
        "display_name": str(payload.get("display_name") or ""),
        "player_id": str(player.get("id") or ""),
        "player_name": str(player.get("name") or ""),
        "position": str(player.get("position") or ""),
        "age": str(player.get("age") or ""),
        "offense_rating": str(player.get("offense_rating") or ""),
        "defense_rating": str(player.get("defense_rating") or ""),
        "shooting_rating": str(player.get("shooting_rating") or ""),
        "playmaking_rating": str(player.get("playmaking_rating") or ""),
        "rebounding_rating": str(player.get("rebounding_rating") or ""),
        "health_risk": str(player.get("health_risk") or ""),
        "upside": str(player.get("upside") or ""),
        "minutes_stability": str(player.get("minutes_stability") or ""),
        "expected_cost_tier": str(player.get("expected_cost_tier") or ""),
        "team_id": str(ctx.get("team_id") or ""),
        "timeline": str(ctx.get("timeline") or ""),
        "need_g": str(needs.get("G") or ""),
        "need_f": str(needs.get("F") or ""),
        "need_c": str(needs.get("C") or ""),
        "cap_flexibility": str(ctx.get("cap_flexibility") or ""),
        "risk_tolerance": str(ctx.get("risk_tolerance") or ""),
        "summary_note": str(payload.get("summary_note") or ""),
        "strengths": str(payload.get("strengths") or ""),
        "concerns": str(payload.get("concerns") or ""),
        "mode": str(payload.get("mode") or ""),
    }


def build_csv_template_text() -> str:
    sample_rows = [_payload_to_csv_row(payload) for payload in demo_payloads()[:2]]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_IMPORT_COLUMNS)
    writer.writeheader()
    for row in sample_rows:
        writer.writerow(row)
    return buffer.getvalue()


def parse_csv_import_text(text: str, default_mode: str = DEFAULT_MODE) -> tuple[List[Dict[str, Any]], List[str]]:
    reader = csv.DictReader(StringIO(text))
    payloads: List[Dict[str, Any]] = []
    errors: List[str] = []

    if not reader.fieldnames:
        return [], ["CSV import needs a header row."]

    missing_headers = [col for col in CSV_REQUIRED_COLUMNS if col not in reader.fieldnames]
    if missing_headers:
        return [], [f"Missing required CSV column(s): {', '.join(missing_headers)}"]

    for row_num, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        try:
            for key in CSV_REQUIRED_COLUMNS:
                if not _csv_cell(row, key):
                    raise ValueError(f"Row {row_num}: `{key}` is required.")

            position = _csv_cell(row, "position").upper()
            if position not in {"G", "F", "C"}:
                raise ValueError(f"Row {row_num}: `position` must be G, F, or C.")

            timeline = _csv_cell(row, "timeline")
            if timeline not in {"win_now", "balanced", "rebuild"}:
                raise ValueError(f"Row {row_num}: `timeline` must be win_now, balanced, or rebuild.")

            mode = _csv_cell(row, "mode") or default_mode
            if mode not in MODE_LABELS:
                raise ValueError(f"Row {row_num}: `mode` must be one of {', '.join(MODE_LABELS.keys())}.")

            payloads.append(
                build_payload_from_form(
                    _csv_cell(row, "display_name") or "CSV Import",
                    _csv_cell(row, "player_id"),
                    _csv_cell(row, "player_name"),
                    position,
                    _csv_int(row, "age", row_num),
                    _csv_float(row, "offense_rating", row_num),
                    _csv_float(row, "defense_rating", row_num),
                    _csv_float(row, "shooting_rating", row_num),
                    _csv_float(row, "playmaking_rating", row_num),
                    _csv_float(row, "rebounding_rating", row_num),
                    _csv_float(row, "health_risk", row_num),
                    _csv_float(row, "upside", row_num),
                    _csv_float(row, "minutes_stability", row_num),
                    _csv_int(row, "expected_cost_tier", row_num),
                    _csv_cell(row, "team_id"),
                    timeline,
                    _csv_float(row, "need_g", row_num),
                    _csv_float(row, "need_f", row_num),
                    _csv_float(row, "need_c", row_num),
                    _csv_float(row, "cap_flexibility", row_num),
                    _csv_float(row, "risk_tolerance", row_num),
                    _csv_cell(row, "summary_note"),
                    _csv_cell(row, "strengths"),
                    _csv_cell(row, "concerns"),
                    mode,
                )
            )
        except ValueError as exc:
            errors.append(str(exc))

    return payloads, errors


def split_csv_duplicates(
    payloads: List[Dict[str, Any]], existing_evaluations: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    existing_keys = {
        (
            str(((row.get("player") or {}).get("id") or "")).strip().lower(),
            str(row.get("team_id") or "").strip().lower(),
        ): row
        for row in existing_evaluations
    }

    unique_payloads: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, str]] = []

    for payload in payloads:
        player = payload.get("player", {}) or {}
        ctx = payload.get("ctx", {}) or {}
        key = (
            str(player.get("id") or "").strip().lower(),
            str(ctx.get("team_id") or "").strip().lower(),
        )
        existing = existing_keys.get(key)
        if existing is None:
            unique_payloads.append(payload)
            continue

        duplicates.append(
            {
                "Player": str(player.get("name") or "Player"),
                "Player ID": str(player.get("id") or "—"),
                "Team": str(ctx.get("team_id") or "—"),
                "Existing Score": format_score(existing.get("overall_score")),
                "Existing Mode": MODE_LABELS.get(existing.get("mode") or DEFAULT_MODE, existing.get("mode") or DEFAULT_MODE),
            }
        )

    return unique_payloads, duplicates


def build_compare_export_markdown(left_detail: Dict[str, Any], right_detail: Dict[str, Any]) -> str:
    left_detail = normalize_detail_for_display(left_detail)
    right_detail = normalize_detail_for_display(right_detail)

    left_player = left_detail.get("player", {}) or {}
    right_player = right_detail.get("player", {}) or {}
    mode = left_detail.get("mode") or right_detail.get("mode") or "pro_wnba"
    roster_need_call = build_roster_need_call(left_detail, right_detail)
    decision_snapshot = build_compare_decision_snapshot(left_detail, right_detail)
    verdicts = build_comparison_verdicts(left_detail, right_detail)

    left_name = left_player.get("name", "Selected Player")
    right_name = right_player.get("name", "Comparison Player")

    lines = [
        f"# {left_name} vs {right_name} - WAIMS-GM Comparison Brief",
        "",
        f"**Mode:** {MODE_LABELS.get(mode, mode)}",
        f"**Primary Call:** {roster_need_call['winner']}",
        "",
        "## Executive Summary",
        compare_summary(left_detail, right_detail),
        "",
        f"## {roster_need_call['title']}",
        roster_need_call["note"],
        "",
        "## Decision Snapshot",
    ]

    if decision_snapshot:
        lines.extend(
            f"- {item['title']}: {item['winner']} - {item['note']}"
            for item in decision_snapshot
        )
    else:
        lines.append("- No decision snapshot available.")

    lines.extend([
        "",
        "## Decision Verdicts",
    ])

    if verdicts:
        lines.extend(
            f"- {item['title']}: {item['winner']} - {item['note']}"
            for item in verdicts
        )
    else:
        lines.append("- No comparison verdicts available.")

    lines.extend(["", "## Component Comparison", f"| Component | {left_name} | Edge | {right_name} |", "|---|---:|---|---:|"])
    for key, label in COMPONENT_LABELS.items():
        left_value = _component_number(left_detail.get("components", {}) or {}, key)
        right_value = _component_number(right_detail.get("components", {}) or {}, key)
        if left_value is None and right_value is None:
            continue

        if left_value is None:
            edge = right_name
        elif right_value is None:
            edge = left_name
        elif abs(left_value - right_value) < 0.01:
            edge = "Even"
        else:
            edge = left_name if left_value > right_value else right_name

        lines.append(f"| {label} | {format_score(left_value)} | {edge} | {format_score(right_value)} |")

    for detail, name in ((left_detail, left_name), (right_detail, right_name)):
        lines.extend(
            [
                "",
                f"## {name} Snapshot",
                f"- Overall Score: {format_score(detail.get('overall_score'))}",
                f"- Recommendation: {clean_action(detail.get('recommended_action'), detail.get('mode'))}",
                f"- Position: {(detail.get('player') or {}).get('position', '—')}",
                f"- Age: {(detail.get('player') or {}).get('age', '—')}",
                f"- Summary Note: {detail.get('summary_note') or 'No summary note.'}",
                "",
                f"### {name} Strengths",
            ]
        )
        strengths = text_block_lines(detail.get("strengths"), "No strengths entered.")
        concerns = text_block_lines(detail.get("concerns"), "No concerns entered.")
        lines.extend(f"- {line}" for line in strengths)
        lines.extend(["", f"### {name} Concerns"])
        lines.extend(f"- {line}" for line in concerns)

    return "\n".join(lines)


def build_export_markdown(detail: Dict[str, Any]) -> str:
    player = detail.get("player", {}) or {}
    ctx = detail.get("ctx", {}) or {}
    mode = detail.get("mode") or "pro_wnba"
    lines = [
        f"# {player.get('name', 'Unknown Player')} — WAIMS-GM Dossier",
        "",
        f"**Mode:** {MODE_LABELS.get(mode, mode)}",
        f"**Recommendation:** {clean_action(detail.get('recommended_action'), mode)}",
        f"**Overall Score:** {format_score(detail.get('overall_score'))}",
        f"**Created:** {format_dt(detail.get('created_at'))}",
        "",
        "## Player Profile",
        f"- Position: {player.get('position', '—')}",
        f"- Age: {player.get('age', '—')}",
        f"- Cost Tier: {player.get('expected_cost_tier', '—')}",
        f"- Health Risk: {player.get('health_risk', '—')}",
        f"- Upside: {player.get('upside', '—')}",
        f"- Minutes Stability: {player.get('minutes_stability', '—')}",
        "",
        "## Executive Memo",
        build_memo(detail),
        "",
        "## Decision Lens",
        build_decision_lens(detail),
        "",
        "## Context Summary",
        summarize_context(ctx),
        "",
        "## Strengths",
    ]
    strengths = [x.strip("•- ").strip() for x in (detail.get("strengths") or "").splitlines() if x.strip()]
    concerns = [x.strip("•- ").strip() for x in (detail.get("concerns") or "").splitlines() if x.strip()]
    if strengths:
        lines.extend([f"- {s}" for s in strengths])
    else:
        lines.append("- No strengths entered.")
    lines.extend(["", "## Concerns"])
    if concerns:
        lines.extend([f"- {c}" for c in concerns])
    else:
        lines.append("- No concerns entered.")

    lines.extend(["", "## Five Layer Diagnostic"])
    for row in compute_five_layer_diagnostic(detail):
        lines.append(f"### {row['layer']} ({row['grade']})")
        lines.append(row["note"])
        lines.append("")

    return "\n".join(lines)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tcMar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tcMar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def add_section_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(12.5)
    r.font.color.rgb = RGBColor(31, 31, 31)


def add_body_paragraph(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r = p.add_run(text)
    r.font.size = Pt(10.5)


def add_bullet_list(doc: Document, text_block: Optional[str], fallback: str) -> None:
    lines = [line.strip("•- ").strip() for line in (text_block or "").splitlines() if line.strip()]
    if not lines:
        lines = [fallback]
    for line in lines:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(line)
        r.font.size = Pt(10.5)


def build_export_docx_bytes(detail: Dict[str, Any]) -> bytes:
    if not WORD_EXPORT_AVAILABLE:
        raise RuntimeError(f"Word export unavailable: {WORD_EXPORT_ERROR or 'python-docx not installed'}")

    player = detail.get("player", {}) or {}
    ctx = detail.get("ctx", {}) or {}
    mode = detail.get("mode") or "pro_wnba"
    assumptions = detail.get("assumptions", {}) or {}
    tension_points = detail.get("tension_points", []) or []

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.65)
    sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.75)
    sec.right_margin = Inches(0.75)

    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(10.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.paragraph_format.space_after = Pt(2)
    r = title.add_run(f"{player.get('name', 'Unknown Player')} — WAIMS-GM Dossier")
    r.bold = True
    r.font.size = Pt(18)
    r.font.color.rgb = RGBColor(24, 24, 24)

    kicker = doc.add_paragraph()
    kicker.paragraph_format.space_after = Pt(8)
    rr = kicker.add_run("Executive Basketball Briefing")
    rr.italic = True
    rr.font.size = Pt(9.5)
    rr.font.color.rgb = RGBColor(95, 90, 82)

    meta = doc.add_table(rows=2, cols=3)
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta.style = "Table Grid"
    meta.autofit = True

    meta_entries = [
        ("Mode", MODE_LABELS.get(mode, mode)),
        ("Recommendation", clean_action(detail.get("recommended_action"), mode)),
        ("Overall Score", format_score(detail.get("overall_score"))),
        ("Position", str(player.get("position", "—"))),
        ("Age", str(player.get("age", "—"))),
        ("Created", format_dt(detail.get("created_at"))),
    ]
    idx = 0
    for row in meta.rows:
        for cell in row.cells:
            label, value = meta_entries[idx]
            idx += 1
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            set_cell_shading(cell, "F6F1E7")
            cell.text = ""
            p1 = cell.paragraphs[0]
            p1.paragraph_format.space_after = Pt(1)
            r1 = p1.add_run(label)
            r1.bold = True
            r1.font.size = Pt(8.5)
            r1.font.color.rgb = RGBColor(95, 90, 82)
            p2 = cell.add_paragraph()
            p2.paragraph_format.space_before = Pt(0)
            r2 = p2.add_run(value)
            r2.font.size = Pt(10.5)

    add_section_heading(doc, "Executive Memo")
    add_body_paragraph(doc, build_memo(detail))

    add_section_heading(doc, "Decision Lens")
    add_body_paragraph(doc, build_decision_lens(detail))

    add_section_heading(doc, "Player Profile")
    prof = doc.add_table(rows=3, cols=2)
    prof.alignment = WD_TABLE_ALIGNMENT.CENTER
    prof.style = "Table Grid"
    prof_entries = [
        ("Cost Tier", str(player.get("expected_cost_tier", "—"))),
        ("Health Risk", str(player.get("health_risk", "—"))),
        ("Upside", str(player.get("upside", "—"))),
        ("Minutes Stability", str(player.get("minutes_stability", "—"))),
        ("Offense / Defense", f"{player.get('offense_rating', '—')} / {player.get('defense_rating', '—')}"),
        ("Shooting / Playmaking / Rebounding", f"{player.get('shooting_rating', '—')} / {player.get('playmaking_rating', '—')} / {player.get('rebounding_rating', '—')}"),
    ]
    idx = 0
    for row in prof.rows:
        for cell in row.cells:
            label, value = prof_entries[idx]
            idx += 1
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            cell.text = ""
            p1 = cell.paragraphs[0]
            p1.paragraph_format.space_after = Pt(1)
            r1 = p1.add_run(label)
            r1.bold = True
            r1.font.size = Pt(8.5)
            r1.font.color.rgb = RGBColor(95, 90, 82)
            p2 = cell.add_paragraph()
            r2 = p2.add_run(value)
            r2.font.size = Pt(10.2)

    add_section_heading(doc, "Context Summary")
    add_body_paragraph(doc, summarize_context(ctx))
    needs = ctx.get("needs_by_position", {}) or {}
    if needs:
        add_body_paragraph(doc, "Positional Needs: " + ", ".join(f"{k}: {v}" for k, v in needs.items()))

    add_section_heading(doc, "Strengths")
    add_bullet_list(doc, detail.get("strengths"), "No strengths entered.")

    add_section_heading(doc, "Concerns")
    add_bullet_list(doc, detail.get("concerns"), "No concerns entered.")

    add_section_heading(doc, "Assumptions")
    if assumptions:
        for k, v in assumptions.items():
            add_body_paragraph(doc, f"{k.replace('_', ' ').title()}: {v}")
    else:
        add_body_paragraph(doc, "No assumptions recorded.")

    add_section_heading(doc, "Tension Points")
    if tension_points:
        for tp in tension_points:
            add_body_paragraph(doc, f"• {tp}")
    else:
        add_body_paragraph(doc, "No major tension points flagged.")

    add_section_heading(doc, "Five Layer Diagnostic")
    for row in compute_five_layer_diagnostic(detail):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(f"{row['layer']} ({row['grade']})")
        r.bold = True
        r.font.size = Pt(11)
        add_body_paragraph(doc, row["note"])

    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer.add_run("WAIMS-GM | Decision-Support Dossier")
    fr.font.size = Pt(8.5)
    fr.font.color.rgb = RGBColor(120, 120, 120)

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()


def main() -> None:
    inject_css()
    render_header()

    if "load_requested" not in st.session_state:
        st.session_state["load_requested"] = False
    if "preferred_mode" not in st.session_state:
        st.session_state["preferred_mode"] = DEFAULT_MODE
    if "preferred_mode_selector" not in st.session_state:
        st.session_state["preferred_mode_selector"] = st.session_state["preferred_mode"]
    if "product_mode" not in st.session_state:
        st.session_state["product_mode"] = st.session_state["preferred_mode"]

    preferred_mode = st.session_state["preferred_mode"]

    with st.sidebar:
        st.markdown("## Runtime")
        if IS_LIVE_ENV:
            st.error(f"{WAIMS_ENV_LABEL} environment")
        else:
            st.success(f"{WAIMS_ENV_LABEL} environment")
        if WAIMS_DEMO_MODE:
            st.caption("Backend: local in-app demo data")
            st.info("Local demo mode is on. No bearer token or backend is required.")
        else:
            st.caption(f"Backend: {API_BASE_URL}")

        st.markdown("## Access")
        token = st.text_input(
            "Bearer token",
            type="password",
            placeholder="Paste your Supabase access token here" if not WAIMS_DEMO_MODE else "Not required in local demo mode",
            disabled=WAIMS_DEMO_MODE,
        )
        if not WAIMS_DEMO_MODE:
            st.caption("Paste only the raw token, not the word Bearer.")
        else:
            st.caption("Interview-safe local mode: seeded demo dossiers run fully in memory.")

        st.markdown("## Mode Focus")
        preferred_mode = st.selectbox(
            "Session mode",
            list(MODE_LABELS.keys()),
            index=list(MODE_LABELS.keys()).index(preferred_mode),
            format_func=lambda x: MODE_LABELS[x],
            key="preferred_mode_selector",
        )
        if preferred_mode != st.session_state["preferred_mode"]:
            st.session_state["preferred_mode"] = preferred_mode
            st.session_state["product_mode"] = preferred_mode
        preferred_playbook = get_mode_playbook(preferred_mode)
        st.caption(preferred_playbook["headline"])
        st.caption(preferred_playbook["weight_note"])

        st.markdown("## Filters")
        mode_scope = st.selectbox(
            "Board scope",
            ["Focused", "All"] + list(MODE_LABELS.keys()),
            index=0,
            format_func=lambda x: (
                f"Focused: {MODE_LABELS[preferred_mode]}"
                if x == "Focused"
                else ("All modes" if x == "All" else MODE_LABELS[x])
            ),
        )
        action_filter = st.selectbox("Recommendation", ["All", "draft", "sign", "pass"], index=0)
        sort_by = st.selectbox("Sort by", ["Created", "Score", "Recommendation", "Mode", "Player Name"], index=0)
        descending = st.checkbox("Descending", value=True)
        hide_placeholder = st.checkbox("Hide placeholder/test junk", value=True)
        load_data = st.button("Load briefing")

        st.markdown("## Manage Selected")
        delete_selected = st.button("Delete selected evaluation")

        st.markdown("## Export Status")
        if WORD_EXPORT_AVAILABLE:
            st.success("Word export ready")
        else:
            st.warning("Word export unavailable")
            st.caption(WORD_EXPORT_ERROR or "Install python-docx to enable Word export.")

    if load_data:
        st.session_state["load_requested"] = True

    if WAIMS_DEMO_MODE:
        st.session_state["load_requested"] = True
        token = token or "demo-local-token"
    else:
        if not token and not st.session_state["load_requested"]:
            st.info("Paste a sandbox bearer token in the sidebar, click 'Load briefing', and the board will populate from Supabase.")
            st.caption("If you want a fast demo board, run scripts\\seed_demo_data.py first.")
            return

        if not token:
            st.warning("A bearer token is required to load the briefing.")
            return

    try:
        raw_evaluations = get_evaluations(token)
    except httpx.HTTPStatusError as e:
        st.error(f"API error loading evaluations: {e.response.status_code} {e.response.text}")
        return
    except Exception as e:
        st.error(f"Unexpected error loading evaluations: {e}")
        return

    mode_filter = preferred_mode if mode_scope == "Focused" else mode_scope

    evaluate_tab, board_tab, dossier_tab, compare_tab = st.tabs(
        ["Create Evaluation", "Board", "Player Dossier", "Compare"]
    )

    with evaluate_tab:
        st.markdown('<div class="section-kicker">Prospect Intake</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Create New Evaluation</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="intake-shell"><div class="intake-blurb">
            Build a new player file, evaluate it against current team context, and save it directly into the board.
            </div></div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("product_mode") != preferred_mode:
            st.session_state["product_mode"] = preferred_mode
        selected_mode = st.selectbox(
            "Product Mode",
            list(MODE_LABELS.keys()),
            index=list(MODE_LABELS.keys()).index(preferred_mode),
            format_func=lambda x: MODE_LABELS[x],
            key="product_mode",
        )
        if selected_mode != st.session_state["preferred_mode"]:
            st.session_state["preferred_mode"] = selected_mode
            st.session_state["preferred_mode_selector"] = selected_mode
        preferred_mode = selected_mode
        mode_presets = PRESETS.get(selected_mode, {})
        render_mode_focus_banner(selected_mode, "create", show_label=False)
        with st.expander("Batch import from CSV", expanded=False):
            st.caption("Upload a CSV, preview the rows, and save them through the same evaluation pipeline used by the intake form.")
            st.download_button(
                "Download CSV template",
                data=build_csv_template_text(),
                file_name="waims_gm_import_template.csv",
                mime="text/csv",
                key="download_csv_template",
            )
            uploaded_csv = st.file_uploader("Upload evaluation CSV", type=["csv"], key="evaluation_csv_upload")
            if uploaded_csv is not None:
                try:
                    csv_text = uploaded_csv.getvalue().decode("utf-8-sig")
                except UnicodeDecodeError:
                    st.error("CSV must be UTF-8 encoded.")
                else:
                    csv_payloads, csv_errors = parse_csv_import_text(csv_text, default_mode=selected_mode)
                    if csv_errors:
                        for error in csv_errors:
                            st.error(error)
                    if csv_payloads:
                        importable_payloads, duplicate_rows = split_csv_duplicates(csv_payloads, raw_evaluations)
                        preview_rows = [
                            {
                                "Player": payload["player"]["name"],
                                "Mode": MODE_LABELS.get(payload.get("mode") or DEFAULT_MODE, payload.get("mode") or DEFAULT_MODE),
                                "Team": payload["ctx"]["team_id"],
                                "Position": payload["player"]["position"],
                                "Score Inputs": f"O {payload['player']['offense_rating']:.0f} / D {payload['player']['defense_rating']:.0f}",
                            }
                            for payload in csv_payloads
                        ]
                        st.dataframe(preview_rows, use_container_width=True, hide_index=True)
                        if duplicate_rows:
                            st.warning(f"{len(duplicate_rows)} row(s) already match an existing player_id + team_id on the board and will be skipped.")
                            st.dataframe(duplicate_rows, use_container_width=True, hide_index=True)
                        if csv_payloads and not importable_payloads:
                            st.info("All uploaded rows already exist on the current board.")
                        if importable_payloads and st.button("Import non-duplicate rows", key="import_csv_rows"):
                            created_count = 0
                            import_errors: List[str] = []
                            last_new_id: Optional[str] = None
                            for idx, payload in enumerate(importable_payloads, start=1):
                                try:
                                    created = create_evaluation(token, payload)
                                    created_count += 1
                                    last_new_id = created.get("evaluation_id") or last_new_id
                                except httpx.HTTPStatusError as exc:
                                    import_errors.append(
                                        f"Row {idx} ({payload['player']['name']}): {exc.response.status_code} {exc.response.text}"
                                    )
                                except Exception as exc:
                                    import_errors.append(f"Row {idx} ({payload['player']['name']}): {exc}")

                            if last_new_id:
                                st.session_state["selected_evaluation_id"] = last_new_id
                            st.session_state["load_requested"] = True
                            if created_count:
                                skipped_count = len(duplicate_rows)
                                summary = f"Imported {created_count} evaluation(s) from CSV."
                                if skipped_count:
                                    summary += f" Skipped {skipped_count} duplicate row(s)."
                                st.success(summary)
                            for error in import_errors:
                                st.error(error)
                            if created_count:
                                st.rerun()
        preset_name = st.selectbox("Preset", ["Custom"] + list(mode_presets.keys()), index=0, key="preset_name")
        preset = mode_presets.get(preset_name, {})
        st.caption(f"Using {MODE_LABELS.get(selected_mode, selected_mode)} presets and recommendation language for this file.")

        with st.form("main_intake_form"):
            st.markdown("**Player identity**")
            c1, c2 = st.columns(2)
            with c1:
                display_name = st.text_input("Display name", value="Chris")
                player_id = st.text_input("Player ID", value="p300")
                player_name = st.text_input("Player name", value="Prospect Wing")
            with c2:
                position = st.selectbox("Position", ["G", "F", "C"], index=["G", "F", "C"].index(preset.get("position", "F")))
                age = st.number_input("Age", min_value=16, max_value=45, value=int(preset.get("age", 23)), step=1)
                expected_cost_tier = st.number_input("Expected cost tier", min_value=0, max_value=10, value=int(preset.get("expected_cost_tier", 2)), step=1)

            st.markdown("**Basketball profile**")
            c3, c4 = st.columns(2)
            with c3:
                offense_rating = st.slider("Offense", 0, 100, int(preset.get("offense_rating", 74)))
                defense_rating = st.slider("Defense", 0, 100, int(preset.get("defense_rating", 79)))
                shooting_rating = st.slider("Shooting", 0, 100, int(preset.get("shooting_rating", 73)))
            with c4:
                playmaking_rating = st.slider("Playmaking", 0, 100, int(preset.get("playmaking_rating", 64)))
                rebounding_rating = st.slider("Rebounding", 0, 100, int(preset.get("rebounding_rating", 71)))
                minutes_stability = st.slider("Minutes stability", 0.0, 1.0, float(preset.get("minutes_stability", 0.72)), 0.01)

            st.markdown("**Risk and projection**")
            c5, c6 = st.columns(2)
            with c5:
                health_risk = st.slider("Health risk", 0.0, 1.0, float(preset.get("health_risk", 0.22)), 0.01)
            with c6:
                upside = st.slider("Upside", 0.0, 1.0, float(preset.get("upside", 0.76)), 0.01)

            st.markdown("**Team context**")
            c7, c8 = st.columns(2)
            with c7:
                team_id = st.text_input("Team ID", value="team-1")
                timeline = st.selectbox("Timeline", ["win_now", "balanced", "rebuild"], index=1)
                cap_flexibility = st.slider("Cap flexibility", 0.0, 1.0, 0.60, 0.01)
            with c8:
                risk_tolerance = st.slider("Risk tolerance", 0.0, 1.0, 0.40, 0.01)
                need_g = st.slider("Need at Guard", 0.0, 1.0, float(preset.get("need_g", 0.55)), 0.01)
                need_f = st.slider("Need at Forward", 0.0, 1.0, float(preset.get("need_f", 0.80)), 0.01)
                need_c = st.slider("Need at Center", 0.0, 1.0, float(preset.get("need_c", 0.35)), 0.01)

            st.markdown("**Scouting rationale**")
            summary_note = st.text_area("Summary note", value=preset.get("summary_note", ""))
            strengths = st.text_area("Strengths", value=preset.get("strengths", ""))
            concerns = st.text_area("Concerns", value=preset.get("concerns", ""))

            submitted = st.form_submit_button("Create evaluation")

        if submitted:
            payload = build_payload_from_form(
                display_name, player_id, player_name, position, age,
                float(offense_rating), float(defense_rating), float(shooting_rating),
                float(playmaking_rating), float(rebounding_rating),
                float(health_risk), float(upside), float(minutes_stability),
                int(expected_cost_tier), team_id, timeline,
                float(need_g), float(need_f), float(need_c),
                float(cap_flexibility), float(risk_tolerance),
                summary_note, strengths, concerns, selected_mode,
            )
            try:
                created = create_evaluation(token, payload)
                new_id = created.get("evaluation_id")
                if new_id:
                    st.session_state["selected_evaluation_id"] = new_id
                st.session_state["load_requested"] = True
                st.success(f"Saved evaluation for {player_name}.")
                st.rerun()
            except httpx.HTTPStatusError as e:
                st.error(f"API error creating evaluation: {e.response.status_code} {e.response.text}")
            except Exception as e:
                st.error(f"Unexpected error creating evaluation: {e}")

    evaluations = prepare_evaluations(raw_evaluations, action_filter, hide_placeholder, mode_filter)
    evaluations = sort_evaluations(evaluations, sort_by, descending)

    if delete_selected:
        selected_id = st.session_state.get("selected_evaluation_id")
        if not selected_id:
            st.error("No evaluation selected.")
        else:
            try:
                delete_evaluation(token, selected_id)
                remaining = [row for row in evaluations if row["id"] != selected_id]
                st.session_state["selected_evaluation_id"] = remaining[0]["id"] if remaining else None
                st.success("Evaluation deleted.")
                st.rerun()
            except httpx.HTTPStatusError as e:
                st.error(f"API error deleting evaluation: {e.response.status_code} {e.response.text}")
            except Exception as e:
                st.error(f"Unexpected error deleting evaluation: {e}")

    detail = None
    selected_id = st.session_state.get("selected_evaluation_id")
    if evaluations:
        existing_ids = {row["id"] for row in evaluations}
        if selected_id not in existing_ids:
            selected_id = evaluations[0]["id"]
            st.session_state["selected_evaluation_id"] = selected_id
    else:
        selected_id = None

    with board_tab:
        render_mode_focus_banner(preferred_mode, "board")
        render_summary_cards(evaluations)
        st.markdown(f"<div class='filter-note'>Showing {len(evaluations)} evaluation(s) after filters and sorting.</div>", unsafe_allow_html=True)
        if mode_scope == "Focused":
            st.caption(f"Board is focused on {MODE_LABELS.get(preferred_mode, preferred_mode)} for this session.")
        elif mode_scope == "All":
            st.caption(f"Showing all modes. Session default remains {MODE_LABELS.get(preferred_mode, preferred_mode)}.")
        else:
            st.caption(f"Board is explicitly filtered to {MODE_LABELS.get(mode_scope, mode_scope)}.")
        selected_id = render_decision_board(evaluations)
        if selected_id:
            st.caption("Open the `Player Dossier` tab for a full-screen file review, or use `Compare` for side-by-side analysis.")

    if selected_id:
        try:
            detail = get_evaluation_detail(token, selected_id)
        except httpx.HTTPStatusError as e:
            st.error(f"API error loading detail: {e.response.status_code} {e.response.text}")
        except Exception as e:
            st.error(f"Unexpected error loading detail: {e}")

    with dossier_tab:
        st.markdown('<div class="section-kicker">Dossier Workspace</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Player Dossier</div>', unsafe_allow_html=True)

        if not evaluations:
            st.info("No evaluation dossiers are available yet. Create a new evaluation or seed demo files first.")
        else:
            dossier_map = {
                f"{(e.get('player') or {}).get('name', 'Player')} | {MODE_LABELS.get(e.get('mode') or 'pro_wnba', e.get('mode') or 'pro_wnba')} | {format_score(e.get('overall_score'))}": e["id"]
                for e in evaluations
            }
            dossier_labels = list(dossier_map.keys())
            current_label = next((label for label, value in dossier_map.items() if value == selected_id), dossier_labels[0])
            control_left, control_mid, control_right = st.columns([1.8, 0.42, 0.42], gap="small")
            with control_left:
                st.markdown('<div class="section-kicker" style="margin-bottom:0.2rem;">Select Player</div>', unsafe_allow_html=True)
                selected_label = st.selectbox(
                    "Select player dossier",
                    dossier_labels,
                    index=dossier_labels.index(current_label),
                    label_visibility="collapsed",
                )
            selected_id = dossier_map[selected_label]
            st.session_state["selected_evaluation_id"] = selected_id

            detail = get_evaluation_detail(token, selected_id)
            render_mode_focus_banner(detail.get("mode") or preferred_mode, "dossier", show_label=False)
            player_name = (detail.get("player") or {}).get("name", "player").replace(" ", "_")

            with control_mid:
                export_md = build_export_markdown(detail)
                st.download_button(
                    "Markdown",
                    data=export_md,
                    file_name=f"{player_name}_waims_gm_dossier.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with control_right:
                if WORD_EXPORT_AVAILABLE:
                    try:
                        export_docx = build_export_docx_bytes(detail)
                        st.download_button(
                            "Word",
                            data=export_docx,
                            file_name=f"{player_name}_waims_gm_dossier.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.warning(f"Word export failed, but the rest of the app is still available. Details: {e}")
                else:
                    st.info("Word export is unavailable on this environment. Markdown export is still available.")

            render_detail(detail, show_diagnostic=True, show_heading=False)

    with compare_tab:
        st.markdown('<div class="section-kicker">Comparison Workspace</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Side-by-Side Compare</div>', unsafe_allow_html=True)

        if len(evaluations) < 2:
            st.info("Add or seed at least two evaluations to unlock compare mode.")
        else:
            compare_map = {
                f"{(e.get('player') or {}).get('name', 'Player')} | {MODE_LABELS.get(e.get('mode') or 'pro_wnba', e.get('mode') or 'pro_wnba')} | {format_score(e.get('overall_score'))}": e["id"]
                for e in evaluations
            }
            compare_labels = list(compare_map.keys())
            primary_label = next((label for label, value in compare_map.items() if value == selected_id), compare_labels[0])
            primary_choice = st.selectbox("Primary dossier", compare_labels, index=compare_labels.index(primary_label), key="compare_primary")
            primary_id = compare_map[primary_choice]
            st.session_state["selected_evaluation_id"] = primary_id

            comparison_candidates = [(label, value) for label, value in compare_map.items() if value != primary_id]
            comparison_labels = [label for label, _ in comparison_candidates]
            compare_choice = st.selectbox("Compare against", comparison_labels, key="compare_secondary")
            compare_id = dict(comparison_candidates)[compare_choice]

            primary_detail = get_evaluation_detail(token, primary_id)
            compare_detail = get_evaluation_detail(token, compare_id)
            render_mode_focus_banner(primary_detail.get("mode") or preferred_mode, "compare", show_label=False)
            if (primary_detail.get("mode") or "") != (compare_detail.get("mode") or ""):
                st.info("These dossiers come from different product modes. Use the comparison directionally rather than as a pure like-for-like grade.")

            compare_export_md = build_compare_export_markdown(primary_detail, compare_detail)
            compare_name = ((compare_detail.get("player") or {}).get("name", "comparison")).replace(" ", "_")
            primary_name = ((primary_detail.get("player") or {}).get("name", "player")).replace(" ", "_")
            st.download_button(
                "Download comparison brief (.md)",
                data=compare_export_md,
                file_name=f"{primary_name}_vs_{compare_name}_waims_gm_compare.md",
                mime="text/markdown",
                key=f"compare_export_{primary_id}",
            )

            render_compare_block(primary_detail, compare_detail)


if __name__ == "__main__":
    main()



