"""
WAIMS GM — Recruiting Prospect Intake
======================================
Step 1: CSV/Excel upload + privacy scan + prospect database
Step 2: hoopR / ESPN stats enrichment (verified NCAA data)
Step 3: Confidence weighting layer

Drop this file into your WAIMS repo and call recruiting_tab() from dashboard.py
"""

import io
import importlib.util
import re
import sqlite3
import time
from datetime import datetime
from urllib.parse import quote_plus
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import openpyxl  # noqa: F401
    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False

# Optional — hoopR stats enrichment via sportsdataverse
HAVE_HOOPR = importlib.util.find_spec("sportsdataverse") is not None

# Optional — requests for NCAA API fallback
try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False


# ── TEMPLATE COLUMNS ─────────────────────────────────────────────────────────
# These are the columns coaches fill in manually — mirrors what most D2/JUCO
# programs already track in their own spreadsheets.

TEMPLATE_COLUMNS_CORE = [
    "prospect_code",
    "position",
    "class_year",
    "current_school",
    "ppg",
    "rpg",
    "apg",
    "fg_pct",
    "staff_grade",
    "contact_stage",
]

TEMPLATE_COLUMNS_ADVANCED = [
    "prospect_code", "position", "class_year", "height_in", "weight_lbs",
    "current_school", "conference", "stars_scout", "scout_source",
    "ppg", "rpg", "apg", "fg_pct", "three_pct", "ft_pct", "per",
    "staff_grade", "fit_score", "notes", "highlight_link",
    "eligibility_status", "contact_stage",
]

RECRUITING_METADATA_COLUMNS = [
    "verified_source",
    "verified_url",
    "verified_updated_at",
    "verified_player_label",
]

RECRUITING_SCHEMA_COLUMNS = TEMPLATE_COLUMNS_ADVANCED + RECRUITING_METADATA_COLUMNS

# Columns that must never contain real names or personal identifiers
SENSITIVE_PATTERNS = [
    r"\bname\b", r"\bfirst\b", r"\blast\b", r"email", r"phone",
    r"mobile", r"\bdob\b", r"birth", r"ssn", r"address", r"instagram",
    r"twitter", r"social", r"cell",
]

# Columns that are allowed to look name-like
ALLOWED_ID_COLS = {"prospect_code", "current_school", "conference"}

RECRUITING_DATA_DIR = Path(__file__).resolve().parent / "data" / "recruiting"
RECRUITING_BOARD_PATH = RECRUITING_DATA_DIR / "prospect_board.csv"
RECRUITING_DB_PATH = RECRUITING_DATA_DIR / "prospect_board.sqlite"

REQUIRED_COLUMNS = [
    "prospect_code",
    "position",
    "class_year",
    "current_school",
]

COLUMN_ALIASES = {
    "prospect id": "prospect_code",
    "prospect_code": "prospect_code",
    "position": "position",
    "pos": "position",
    "class": "class_year",
    "year": "class_year",
    "class_year": "class_year",
    "school": "current_school",
    "current_school": "current_school",
    "conference": "conference",
    "stars": "stars_scout",
    "star_rating": "stars_scout",
    "stars_scout": "stars_scout",
    "source": "scout_source",
    "scout_source": "scout_source",
    "points": "ppg",
    "points_per_game": "ppg",
    "ppg": "ppg",
    "rebounds": "rpg",
    "rebounds_per_game": "rpg",
    "rpg": "rpg",
    "assists": "apg",
    "assists_per_game": "apg",
    "apg": "apg",
    "fg%": "fg_pct",
    "fg_pct": "fg_pct",
    "3pt%": "three_pct",
    "3p_pct": "three_pct",
    "three_pct": "three_pct",
    "ft%": "ft_pct",
    "ft_pct": "ft_pct",
    "per": "per",
    "staff_grade": "staff_grade",
    "fit": "fit_score",
    "fit_score": "fit_score",
    "notes": "notes",
    "video": "highlight_link",
    "highlight_link": "highlight_link",
    "eligibility": "eligibility_status",
    "eligibility_status": "eligibility_status",
    "contact": "contact_stage",
    "contact_stage": "contact_stage",
}

CLASS_YEAR_NORMALIZATION = {
    "freshman": "FR",
    "fr": "FR",
    "sophomore": "SO",
    "so": "SO",
    "junior": "JR",
    "jr": "JR",
    "senior": "SR",
    "sr": "SR",
    "grad": "GRAD",
    "graduate": "GRAD",
    "gr": "GRAD",
    "juco1": "JUCO-1",
    "juco-1": "JUCO-1",
    "juco2": "JUCO-2",
    "juco-2": "JUCO-2",
}

POSITION_NORMALIZATION = {
    "pg": "PG",
    "sg": "SG",
    "sf": "SF",
    "pf": "PF",
    "c": "C",
    "g": "G",
    "f": "F",
}

CONTACT_STAGE_NORMALIZATION = {
    "none": "None",
    "identified": "Identified",
    "contacted": "Contacted",
    "visit": "Visit",
    "offer": "Offer",
    "signed": "Signed",
    "portal": "Portal",
}

ELIGIBILITY_NORMALIZATION = {
    "available": "Available",
    "committed": "Committed",
    "signed": "Signed",
    "portal": "Portal",
    "juco-eligible": "JUCO-eligible",
    "juco eligible": "JUCO-eligible",
}


def _download_excel_button(label: str, frame_map: dict[str, pd.DataFrame], file_name: str, key: str) -> None:
    if not HAVE_OPENPYXL:
        st.button(label, disabled=True, key=f"{key}_disabled", width="stretch")
        st.caption("Excel download unavailable until `openpyxl` is installed. CSV export still works.")
        return

    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        for sheet_name, df in frame_map.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    excel_buf.seek(0)
    st.download_button(
        label,
        data=excel_buf.getvalue(),
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
        width="stretch",
    )


def _render_recruiting_header() -> tuple[float, float]:
    st.header("Recruiting Prospect Board")
    st.caption(
        "Upload your prospect list to score and rank players. "
        "Game stats from NCAA data are treated as the most reliable signal. "
        "Your own scouting grades and star ratings add context on top."
    )

    with st.expander("How much should each source count toward the score?", expanded=False):
        st.caption(
            "Verified NCAA game stats are always weighted highest - they are the most objective signal. "
            "Your staff grades and scouting star ratings still count, but you can turn them up or down "
            "depending on how much you trust those sources for this batch of prospects."
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            scout_weight = st.slider(
                "Scouting star rating weight",
                min_value=0.0, max_value=1.0, value=0.5, step=0.05,
                help="On3, 247Sports, JucoRecruiting star ratings",
            )
        with col2:
            fit_weight = st.slider(
                "Staff evaluation weight",
                min_value=0.0, max_value=1.0, value=0.8, step=0.05,
                help="Internal staff grade and program fit score",
            )
        with col3:
            st.markdown("**Source reference**")
            for source, weight in SOURCE_WEIGHTS.items():
                bar_w = int(weight * 100)
                color = "#16a34a" if weight == 1.0 else ("#d97706" if weight >= 0.5 else "#dc2626")
                st.markdown(
                    f'<div style="margin-bottom:4px;">'
                    f'<div style="font-size:11px;color:#475569;">{source}</div>'
                    f'<div style="height:6px;background:#e5e7eb;border-radius:3px;overflow:hidden;">'
                    f'<div style="width:{bar_w}%;height:100%;background:{color};"></div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    return scout_weight, fit_weight


def _render_template_download_section() -> None:
    st.subheader("Step 1 - Get the template")
    st.caption(
        "Download the short template below. Fill in one row per prospect. "
        "Use a code like PROS-001 instead of real names - this keeps the data safe if you ever share the file."
    )

    core_df = pd.DataFrame(columns=TEMPLATE_COLUMNS_CORE)
    core_df.loc[0] = [
        "PROS-001", "PG", "JUCO-2", "Example Community College",
        18.5, 4.2, 6.1, 0.47, 7, "Contacted",
    ]
    instructions_df = pd.DataFrame([{
        "prospect_code": "Use a code like PROS-001 (no real names)",
        "position": "PG / SG / SF / PF / C",
        "class_year": "FR / SO / JR / SR / GRAD / JUCO-1 / JUCO-2",
        "current_school": "Full school name - used to look up stats automatically",
        "ppg": "Points per game (leave blank if unknown)",
        "rpg": "Rebounds per game",
        "apg": "Assists per game",
        "fg_pct": "Field goal percent as decimal e.g. 0.47 for 47%",
        "staff_grade": "Your grade for this player, 1-10",
        "contact_stage": "None / Identified / Contacted / Visit / Offer / Signed",
    }])

    col1, col2 = st.columns(2)
    with col1:
        _download_excel_button(
            "⬇ Download short template (10 columns)",
            frame_map={
                "How to fill this in": instructions_df,
                "Prospects": core_df,
            },
            file_name="waims_prospects.xlsx",
            key="download_core_template_xlsx",
        )
    with col2:
        st.download_button(
            "⬇ Download as CSV instead",
            data=core_df.to_csv(index=False),
            file_name="waims_prospects.csv",
            mime="text/csv",
            width="stretch",
        )

    with st.expander("Need more columns? Download the full template", expanded=False):
        st.caption(
            "The full template has 22 columns including star ratings, height, weight, "
            "highlight links, and eligibility status. Use this if you track more detail."
        )
        full_df = pd.DataFrame(columns=TEMPLATE_COLUMNS_ADVANCED)
        st.download_button(
            "⬇ Download full template (22 columns)",
            data=full_df.to_csv(index=False),
            file_name="waims_prospects_full.csv",
            mime="text/csv",
            width="stretch",
        )


def _coach_friendly_confidence(confidence: str, score: float) -> tuple[str, str]:
    if score >= 75:
        rec = "Strong fit - worth pursuing"
        color = "#16a34a"
    elif score >= 55:
        rec = "Worth a closer look"
        color = "#d97706"
    elif score > 0:
        rec = "Monitor - more data needed"
        color = "#94a3b8"
    else:
        rec = "Not enough data to score yet"
        color = "#94a3b8"

    if "High" in confidence:
        source_note = " · Scored from game stats"
    elif "Moderate" in confidence:
        source_note = " · Partial stats + your grades"
    else:
        source_note = " · Based on your grades only"
    return rec + source_note, color


def _stats_nudge_html(row, color: str) -> str:
    school = str(row.get("current_school", "")).strip()
    has_stats = pd.notna(row.get("ppg")) and float(row.get("ppg", 0)) > 0
    if school and not has_stats:
        return (
            f'<div style="margin-top:6px;font-size:11px;color:{color};'
            f'background:{color}11;padding:4px 8px;border-radius:6px;display:inline-block;">'
            f'Stats not yet loaded for {school} - use Step 3 below to pull them</div>'
        )
    return ""


STEP_3_HEADER = "Step 3 - Pull verified game stats from NCAA"
STEP_3_CAPTION = (
    "Use official NCAA / ESPN sources to verify the stat line for a prospect. "
    "Auto roster matching is optional when available, but the reliable path is: "
    "open the official source, confirm the numbers, and apply the verified stat line."
)


def _external_search_links(school_name: str) -> dict[str, str]:
    query = quote_plus(school_name.strip())
    return {
        "ESPN search": f"https://www.espn.com/search/_/q/{query}",
        "NCAA search": f"https://www.ncaa.com/search?query={query}",
    }


def _normalize_column_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def _normalize_uploaded_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    rename_map: dict[str, str] = {}
    for column in df.columns:
        raw = str(column).strip()
        alias_key = _normalize_column_name(raw).replace("_", " ")
        canonical = COLUMN_ALIASES.get(alias_key) or COLUMN_ALIASES.get(_normalize_column_name(raw)) or _normalize_column_name(raw)
        rename_map[column] = canonical
    return df.rename(columns=rename_map), rename_map


def _persist_board(df: pd.DataFrame) -> None:
    RECRUITING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RECRUITING_BOARD_PATH, index=False)
    with sqlite3.connect(RECRUITING_DB_PATH) as conn:
        df.to_sql("prospects", conn, if_exists="replace", index=False)


def _load_persisted_board() -> pd.DataFrame | None:
    if RECRUITING_DB_PATH.exists():
        try:
            with sqlite3.connect(RECRUITING_DB_PATH) as conn:
                return pd.read_sql_query("SELECT * FROM prospects", conn)
        except Exception:
            pass
    if not RECRUITING_BOARD_PATH.exists():
        return None
    try:
        return pd.read_csv(RECRUITING_BOARD_PATH)
    except Exception:
        return None


def _normalize_recruiting_values(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for col in RECRUITING_SCHEMA_COLUMNS:
        if col not in normalized.columns:
            normalized[col] = ""

    for col in ["prospect_code", "position", "class_year", "current_school", "conference", "scout_source", "notes", "highlight_link", "eligibility_status", "contact_stage"]:
        normalized[col] = normalized[col].fillna("").astype(str).str.strip()

    normalized["position"] = normalized["position"].str.lower().map(POSITION_NORMALIZATION).fillna(normalized["position"].str.upper())
    normalized["class_year"] = normalized["class_year"].str.lower().map(CLASS_YEAR_NORMALIZATION).fillna(normalized["class_year"].str.upper())
    normalized["contact_stage"] = normalized["contact_stage"].str.lower().map(CONTACT_STAGE_NORMALIZATION).fillna(normalized["contact_stage"])
    normalized["eligibility_status"] = normalized["eligibility_status"].str.lower().map(ELIGIBILITY_NORMALIZATION).fillna(normalized["eligibility_status"])
    normalized["prospect_code"] = normalized["prospect_code"].str.upper()
    normalized["current_school"] = normalized["current_school"].str.replace(r"\s+", " ", regex=True)
    return normalized


def _persistable_board(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [col for col in ["prospect_score", "confidence"] if col in df.columns]
    return df.drop(columns=drop_cols, errors="ignore")


def _candidate_value(row: pd.Series, keys: list[str]) -> float | str | None:
    for key in keys:
        if key in row and pd.notna(row[key]):
            return row[key]
    return None


def _best_candidate_labels(result: pd.DataFrame, prospect_row: pd.Series) -> list[str]:
    if "athlete_display_name" not in result.columns:
        return []

    scored: list[tuple[int, str]] = []
    target_pos = str(prospect_row.get("position") or "").upper()
    target_class = str(prospect_row.get("class_year") or "").upper()
    for _, row in result.iterrows():
        score = 0
        row_pos = str(_candidate_value(row, ["position", "athlete_position_abbreviation"]) or "").upper()
        if target_pos and row_pos and (row_pos == target_pos or row_pos.startswith(target_pos) or target_pos.startswith(row_pos)):
            score += 2
        row_class = str(_candidate_value(row, ["class", "athlete_class", "experience"]) or "").upper()
        if target_class and row_class and target_class in row_class:
            score += 1
        label = str(row.get("athlete_display_name") or "")
        if label:
            scored.append((score, label))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [label for _, label in scored]


def _safe_float(value):
    if value in ("", None):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _apply_verified_stats_to_board(
    df: pd.DataFrame,
    prospect_code: str,
    stat_updates: dict[str, float | None],
    source_label: str,
    source_url: str = "",
    player_label: str = "",
) -> pd.DataFrame:
    updated = df.copy()
    mask = updated["prospect_code"].astype(str) == str(prospect_code)
    if not mask.any():
        return updated

    for key, value in stat_updates.items():
        if key not in updated.columns:
            updated[key] = pd.NA
        updated.loc[mask, key] = value

    meta_values = {
        "verified_source": source_label.strip(),
        "verified_url": source_url.strip(),
        "verified_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "verified_player_label": player_label.strip(),
    }
    for key, value in meta_values.items():
        if key not in updated.columns:
            updated[key] = ""
        updated.loc[mask, key] = value
    return updated


def validate_recruiting_upload(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    cleaned, rename_map = _normalize_uploaded_columns(df)
    errors: list[str] = []
    warnings: list[str] = []

    missing = [column for column in REQUIRED_COLUMNS if column not in cleaned.columns]
    if missing:
        errors.append(f"Missing required column(s): {', '.join(missing)}")

    duplicate_cols = [col for col in cleaned.columns if list(cleaned.columns).count(col) > 1]
    if duplicate_cols:
        errors.append(f"Duplicate column names after normalization: {', '.join(sorted(set(duplicate_cols)))}")

    unknown_columns = [col for col in cleaned.columns if col not in RECRUITING_SCHEMA_COLUMNS]
    if unknown_columns:
        warnings.append(f"Unrecognized column(s) will be ignored: {', '.join(unknown_columns)}")
        cleaned = cleaned[[col for col in cleaned.columns if col in RECRUITING_SCHEMA_COLUMNS]]

    if errors:
        return cleaned, errors, warnings

    cleaned = _normalize_recruiting_values(cleaned)

    duplicate_codes = cleaned["prospect_code"][cleaned["prospect_code"].duplicated(keep=False) & cleaned["prospect_code"].ne("")]
    if not duplicate_codes.empty:
        errors.append(f"Duplicate prospect code(s): {', '.join(sorted(duplicate_codes.unique()))}")

    bad_positions = sorted({value for value in cleaned["position"].unique() if value and value not in {"PG", "SG", "SF", "PF", "C", "G", "F"}})
    if bad_positions:
        warnings.append(f"Some position values are non-standard and may score oddly: {', '.join(bad_positions)}")

    blank_school = int(cleaned["current_school"].eq("").sum())
    if blank_school:
        warnings.append(f"{blank_school} row(s) are missing school name, so verified stats enrichment will not work for them.")

    blank_code = int(cleaned["prospect_code"].eq("").sum())
    if blank_code:
        errors.append(f"{blank_code} row(s) are missing prospect_code.")

    numeric_cols = [
        "height_in", "weight_lbs", "stars_scout", "ppg", "rpg", "apg",
        "fg_pct", "three_pct", "ft_pct", "per", "staff_grade", "fit_score",
    ]
    for col in numeric_cols:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    renamed_columns = {str(old): new for old, new in rename_map.items() if str(old) != new}
    if renamed_columns:
        rename_summary = ", ".join(f"{old} -> {new}" for old, new in renamed_columns.items())
        warnings.append(f"Normalized incoming column names: {rename_summary}")

    return cleaned[RECRUITING_SCHEMA_COLUMNS].copy(), errors, warnings


# ── CONFIDENCE / WEIGHTING ────────────────────────────────────────────────────

SOURCE_WEIGHTS = {
    "ESPN / hoopR (verified NCAA)":  1.00,
    "NCAA.com official":             1.00,
    "Staff film evaluation":         0.75,
    "On3 / 247Sports ranking":       0.50,
    "JucoRecruiting.com":            0.50,
    "Self-reported by athlete":      0.30,
    "Unknown / other":               0.20,
}

STAT_CONFIDENCE_NOTE = (
    "Verified NCAA stats (ESPN/hoopR) are weighted at 100% confidence. "
    "Scouting rankings and self-reported data carry lower weight by default — "
    "adjust the sliders below to reflect how much you trust each source."
)


# ── PRIVACY SCAN ──────────────────────────────────────────────────────────────

def scan_for_identifiers(df: pd.DataFrame) -> list[str]:
    """Flag columns and values that may contain direct identifiers."""
    findings = []
    norm = {col: col.strip().lower() for col in df.columns}

    for original, normalized in norm.items():
        if normalized in ALLOWED_ID_COLS:
            continue
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, normalized):
                findings.append(
                    f"Column '{original}' may contain personal identifiers. "
                    f"Replace with anonymous codes like PROS-001."
                )
                break

    # Scan first 20 rows of text values
    text_blob = " ".join(
        df.astype(str).fillna("").head(20).stack().tolist()
    )
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text_blob):
        findings.append("Possible email address detected in uploaded values.")
    if re.search(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}", text_blob):
        findings.append("Possible phone number detected in uploaded values.")

    return findings


def _load_hoopr_client():
    if not HAVE_HOOPR:
        return None, "sportsdataverse is not installed."
    try:
        import sportsdataverse.mbb as mbb  # type: ignore
        return mbb, None
    except Exception as exc:
        return None, str(exc)


VERIFIED_SOURCE_OPTIONS = [
    "NCAA player / team page",
    "ESPN player / team page",
    "NJCAA / JUCO official page",
    "Official school stat page",
    "Official box score / stat sheet",
]


# ── STATS ENRICHMENT ──────────────────────────────────────────────────────────

def lookup_player_stats_hoopr(school_name: str, season: int = 2025) -> pd.DataFrame | None:
    """
    Pull team roster and season stats via hoopR / sportsdataverse.
    Returns a DataFrame of players at that school, or None on failure.
    Requires: pip install sportsdataverse
    """
    mbb, _ = _load_hoopr_client()
    if mbb is None:
        return None
    try:
        roster = mbb.load_mbb_team_box(seasons=[season])
        if roster is None or len(roster) == 0:
            return None
        school_df = roster[
            roster["team_location"].str.lower().str.contains(
                school_name.lower(), na=False
            )
        ]
        return school_df if len(school_df) > 0 else None
    except Exception:
        return None


def lookup_school_stats_ncaa_api(school_name: str) -> dict | None:
    """
    Lightweight fallback — NCAA.com unofficial API for school info.
    Returns basic school metadata or None.
    Docs: https://github.com/henrygd/ncaa-api
    """
    if not HAVE_REQUESTS:
        return None
    try:
        # Public ncaa.com endpoint — returns school list with slugs
        url = "https://ncaa-api.henrygd.me/schools"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return None
        schools = resp.json()
        # Find closest match
        for school in schools:
            if school_name.lower() in school.get("name", "").lower():
                return school
        return None
    except Exception:
        return None


# ── COMPOSITE SCORE ───────────────────────────────────────────────────────────

def calculate_prospect_score(
    row: pd.Series,
    stat_weight: float = 1.0,
    scout_weight: float = 0.5,
    fit_weight: float = 0.8,
) -> float:
    """
    Weighted composite prospect score 0-100.
    Verified stats anchor the score. Scouting and fit are adjustable context.
    """
    scores = []

    # Verified stat contribution (normalized per typical D2 averages)
    stat_score = 0.0
    stat_count = 0
    if pd.notna(row.get("ppg")) and float(row["ppg"]) > 0:
        stat_score += min(float(row["ppg"]) / 25.0, 1.0) * 30  # 25 ppg = max
        stat_count += 1
    if pd.notna(row.get("fg_pct")) and float(row["fg_pct"]) > 0:
        stat_score += min(float(row["fg_pct"]) / 0.55, 1.0) * 20  # 55% = max
        stat_count += 1
    if pd.notna(row.get("rpg")) and float(row["rpg"]) > 0:
        pos = str(row.get("position", "")).upper()
        bench = 10.0 if pos in ("PF", "C") else 6.0
        stat_score += min(float(row["rpg"]) / bench, 1.0) * 15
        stat_count += 1
    if pd.notna(row.get("apg")) and float(row["apg"]) > 0:
        pos = str(row.get("position", "")).upper()
        bench = 8.0 if pos in ("PG", "SG") else 4.0
        stat_score += min(float(row["apg"]) / bench, 1.0) * 15
        stat_count += 1
    if stat_count > 0:
        scores.append(stat_score * stat_weight)

    # Scout star rating contribution (1-5 stars → 0-20 pts)
    if pd.notna(row.get("stars_scout")) and float(row["stars_scout"]) > 0:
        scout_score = (float(row["stars_scout"]) / 5.0) * 20
        scores.append(scout_score * scout_weight)

    # Staff grade + fit (1-10 → 0-100, normalized to 0-20 pts each)
    if pd.notna(row.get("staff_grade")) and float(row["staff_grade"]) > 0:
        scores.append((float(row["staff_grade"]) / 10.0) * 20 * fit_weight)
    if pd.notna(row.get("fit_score")) and float(row["fit_score"]) > 0:
        scores.append((float(row["fit_score"]) / 10.0) * 20 * fit_weight)

    if not scores:
        return 0.0
    return round(min(sum(scores), 100.0), 1)


def get_confidence_label(row: pd.Series) -> str:
    """Describe confidence level based on how many verified data points exist."""
    verified = sum([
        pd.notna(row.get("ppg")) and float(row.get("ppg", 0)) > 0,
        pd.notna(row.get("fg_pct")) and float(row.get("fg_pct", 0)) > 0,
        pd.notna(row.get("rpg")) and float(row.get("rpg", 0)) > 0,
        pd.notna(row.get("apg")) and float(row.get("apg", 0)) > 0,
    ])
    if verified >= 3:
        return "High — verified stats anchor"
    elif verified >= 1:
        return "Moderate — partial stats"
    elif pd.notna(row.get("staff_grade")):
        return "Low — staff evaluation only"
    else:
        return "Unscored — no data"


# ── STATUS COLOR HELPERS ──────────────────────────────────────────────────────

def _status_color(score: float) -> tuple[str, str]:
    if score >= 75:
        return "#16a34a", "#dcfce7"
    elif score >= 55:
        return "#d97706", "#fef3c7"
    elif score > 0:
        return "#dc2626", "#fee2e2"
    return "#94a3b8", "#f1f5f9"


def _stage_badge(stage: str) -> str:
    colors = {
        "Signed":    ("#166534", "#dcfce7"),
        "Offer":     ("#1d4ed8", "#dbeafe"),
        "Visit":     ("#7c3aed", "#ede9fe"),
        "Contacted": ("#d97706", "#fef3c7"),
        "Identified":("#475569", "#f1f5f9"),
        "None":      ("#94a3b8", "#f8fafc"),
        "Portal":    ("#dc2626", "#fee2e2"),
    }
    c, bg = colors.get(stage, ("#94a3b8", "#f1f5f9"))
    return (
        f'<span style="background:{bg};color:{c};padding:2px 8px;'
        f'border-radius:999px;font-size:11px;font-weight:700;'
        f'border:1px solid {c}33;">{stage}</span>'
    )


# ── MAIN TAB ──────────────────────────────────────────────────────────────────

def recruiting_tab():
    """Main Streamlit recruiting tab - call from dashboard.py"""

    scout_weight, fit_weight = _render_recruiting_header()

    if "recruiting_board_df" not in st.session_state:
        st.session_state["recruiting_board_df"] = None

    st.divider()
    _render_template_download_section()

    st.divider()

    st.subheader("Step 2 — Upload your prospect list")
    st.caption(
        "CSV or Excel accepted. The tool will flag any columns that look like "
        "they contain real names or personal identifiers before processing."
    )

    uploaded = st.file_uploader(
        "Upload prospect CSV or Excel",
        type=["csv", "xlsx", "xls"],
        key="recruiting_upload",
    )

    active_source = "uploaded file"
    validation_warnings: list[str] = []
    df: pd.DataFrame | None = None

    if uploaded is not None:
        try:
            if uploaded.name.endswith(".csv"):
                raw_df = pd.read_csv(io.BytesIO(uploaded.read()))
            else:
                raw_df = pd.read_excel(io.BytesIO(uploaded.read()))
        except Exception as e:
            st.error(f"Could not read file: {e}")
            return

        findings = scan_for_identifiers(raw_df)
        if findings:
            st.error("Upload blocked - the file may contain direct identifiers.")
            for f in findings:
                st.write(f"- {f}")
            st.info(
                "Replace any real names, emails, or phone numbers with anonymous codes "
                "like PROS-001 and re-upload."
            )
            return

        df, validation_errors, validation_warnings = validate_recruiting_upload(raw_df)
        with st.expander("Upload validation report", expanded=bool(validation_errors or validation_warnings)):
            if validation_errors:
                st.error("The upload needs fixes before WAIMS can use it.")
                for error in validation_errors:
                    st.markdown(f"- {error}")
            else:
                st.success("Validation passed.")
            for warning in validation_warnings:
                st.markdown(f"- {warning}")
        if validation_errors:
            st.info("Fix the columns or values listed above and upload again. The board was not changed.")
            return

        st.session_state["recruiting_board_df"] = df.copy()
        _persist_board(_persistable_board(df))
        st.success(f"File accepted - {len(df)} prospects loaded and saved locally.")
    else:
        if st.session_state.get("recruiting_board_df") is not None:
            df = st.session_state["recruiting_board_df"].copy()
            active_source = "current session board"
        else:
            persisted = _load_persisted_board()
            if persisted is not None:
                df, validation_errors, validation_warnings = validate_recruiting_upload(persisted)
                if validation_errors:
                    st.warning("A saved recruiting board exists, but it needs cleanup before WAIMS can use it again.")
                    for error in validation_errors:
                        st.markdown(f"- {error}")
                    st.info("Upload a fresh template to continue.")
                    return
                st.session_state["recruiting_board_df"] = df.copy()
                active_source = f"saved board ({RECRUITING_BOARD_PATH.name})"
                st.info("Loaded the last saved recruiting board automatically.")
            else:
                st.info(
                    "No file uploaded yet. Download the template above, fill it in, "
                    "and upload it here to see your prospect board."
                )
                return

    st.caption(f"Current board source: {active_source}.")
    if validation_warnings:
        st.caption("Any non-blocking upload issues were normalized automatically. Open the validation report above if you want details.")
    control_left, control_right = st.columns(2, gap="small")
    with control_left:
        st.caption(f"Saved board path: `{RECRUITING_DB_PATH}`")
    with control_right:
        if st.button("Clear saved board", key="clear_saved_recruiting_board", width="stretch"):
            st.session_state["recruiting_board_df"] = None
            if RECRUITING_BOARD_PATH.exists():
                RECRUITING_BOARD_PATH.unlink()
            if RECRUITING_DB_PATH.exists():
                RECRUITING_DB_PATH.unlink()
            st.success("Saved recruiting board cleared.")
            st.rerun()

    # Composite score
    df["prospect_score"] = df.apply(
        lambda row: calculate_prospect_score(row, 1.0, scout_weight, fit_weight),
        axis=1,
    )
    df["confidence"] = df.apply(get_confidence_label, axis=1)
    df = df.sort_values("prospect_score", ascending=False).reset_index(drop=True)

    # ── Summary cards ──
    st.divider()
    st.subheader("Prospect Board")

    total = len(df)
    available = len(df[df["eligibility_status"].str.lower().str.contains("available|portal|juco", na=False)])
    high_conf = len(df[df["confidence"].str.startswith("High")])
    top_score = df["prospect_score"].max() if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total prospects", total)
    c2.metric("Available / Portal", available)
    c3.metric("High confidence", high_conf)
    c4.metric("Top score", f"{top_score:.0f}/100")

    st.caption(
        "Scores are weighted by source confidence. "
        "Verified NCAA stats anchor at 100% — scouting ratings and staff grades are adjustable above."
    )

    # ── Filters ──
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        pos_filter = st.multiselect(
            "Position",
            options=sorted(df["position"].dropna().unique()),
            default=[],
            key="rec_pos_filter",
        )
    with filter_col2:
        stage_filter = st.multiselect(
            "Contact stage",
            options=sorted(df["contact_stage"].dropna().unique()),
            default=[],
            key="rec_stage_filter",
        )
    with filter_col3:
        class_filter = st.multiselect(
            "Class year",
            options=sorted(df["class_year"].dropna().unique()),
            default=[],
            key="rec_class_filter",
        )

    filtered = df.copy()
    if pos_filter:
        filtered = filtered[filtered["position"].isin(pos_filter)]
    if stage_filter:
        filtered = filtered[filtered["contact_stage"].isin(stage_filter)]
    if class_filter:
        filtered = filtered[filtered["class_year"].isin(class_filter)]

    # ── Prospect cards ──
    st.markdown(f"Showing **{len(filtered)}** prospects")

    for _, row in filtered.iterrows():
        color, bg = _status_color(row["prospect_score"])
        stage_html = _stage_badge(row.get("contact_stage", "None"))
        confidence_text, conf_color = _coach_friendly_confidence(str(row["confidence"]), float(row["prospect_score"]))

        # Position label
        pos_label = row.get("position", "—") or "—"
        class_label = row.get("class_year", "—") or "—"
        school_label = row.get("current_school", "—") or "—"

        # Stat mini-row
        stats_html = ""
        stat_pairs = [
            ("PPG", row.get("ppg")), ("RPG", row.get("rpg")),
            ("APG", row.get("apg")), ("FG%", row.get("fg_pct")),
        ]
        for label, val in stat_pairs:
            if pd.notna(val) and float(val) > 0:
                display = f"{val:.0%}" if label == "FG%" else f"{val:.1f}"
                stats_html += (
                    f'<div style="text-align:center;min-width:48px;">'
                    f'<div style="font-size:14px;font-weight:700;color:#0f172a;">{display}</div>'
                    f'<div style="font-size:10px;color:#64748b;text-transform:uppercase;">{label}</div>'
                    f'</div>'
                )

        card_html = (
            f'<div style="background:{bg}22;border:1px solid #e2e8f0;'
            f'border-left:5px solid {color};border-radius:12px;'
            f'padding:14px 16px;margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">'
            f'<div>'
            f'<div style="font-size:16px;font-weight:700;color:#0f172a;">'
            f'{row.get("prospect_code","—")} &nbsp;'
            f'<span style="font-size:13px;font-weight:500;color:#64748b;">{pos_label} · {class_label}</span>'
            f'</div>'
            f'<div style="font-size:12px;color:#475569;margin-top:3px;">{school_label}</div>'
            f'</div>'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
            f'{stage_html}'
            f'<span style="font-size:20px;font-weight:700;color:{color};">{row["prospect_score"]:.0f}</span>'
            f'<span style="font-size:11px;color:#94a3b8;">/100</span>'
            f'</div></div>'
        )

        if stats_html:
            card_html += (
                f'<div style="display:flex;gap:16px;margin-top:10px;'
                f'padding-top:10px;border-top:1px solid #e5e7eb;flex-wrap:wrap;">'
                f'{stats_html}</div>'
            )

        card_html += (
            f'<div style="margin-top:8px;font-size:11px;color:{conf_color};">'
            f'{confidence_text}</div>'
        )

        if pd.notna(row.get("notes")) and str(row["notes"]).strip():
            card_html += (
                f'<div style="margin-top:6px;font-size:12px;color:#475569;">'
                f'{str(row["notes"])[:200]}</div>'
            )

        verified_source = str(row.get("verified_source") or "").strip()
        verified_updated = str(row.get("verified_updated_at") or "").strip()
        if verified_source:
            verified_note = verified_source
            if verified_updated:
                verified_note += f" · {verified_updated}"
            card_html += (
                f'<div style="margin-top:6px;font-size:11px;color:#1d4ed8;">'
                f'Verified source: {verified_note}</div>'
            )

        card_html += _stats_nudge_html(row, conf_color)
        card_html += '</div>'
        st.markdown(card_html, unsafe_allow_html=True)

    # ── Stats enrichment section ──
    st.divider()
    st.subheader(STEP_3_HEADER)
    st.caption(STEP_3_CAPTION)
    prospect_options = filtered["prospect_code"].dropna().tolist()
    if prospect_options:
        sel_prospect = st.selectbox(
            "Select prospect to verify",
            options=prospect_options,
            key="rec_enrich_select",
        )
        sel_row = filtered[filtered["prospect_code"] == sel_prospect].iloc[0]
        school = str(sel_row.get("current_school", "") or "").strip()
        links = _external_search_links(school) if school else {}
        ncaa_result = lookup_school_stats_ncaa_api(school) if school else None
        _, hoopr_error = _load_hoopr_client()

        info_col, auto_col = st.columns([1.2, 1.0], gap="large")
        with info_col:
            st.markdown("**Official lookup**")
            if school:
                st.caption(f"Prospect `{sel_prospect}` is currently tied to **{school}**.")
                if ncaa_result and ncaa_result.get("name"):
                    st.caption(f"NCAA school match: {ncaa_result.get('name')}")
                if links:
                    st.markdown(f"- [Search {school} on ESPN]({links['ESPN search']})")
                    st.markdown(f"- [Search {school} on NCAA.com]({links['NCAA search']})")
            else:
                st.warning("This prospect does not have a school name yet, so official lookup links cannot be generated.")

            st.markdown("**Current board stats**")
            stats_preview = pd.DataFrame(
                [
                    {
                        "PPG": sel_row.get("ppg"),
                        "RPG": sel_row.get("rpg"),
                        "APG": sel_row.get("apg"),
                        "FG%": sel_row.get("fg_pct"),
                        "3PT%": sel_row.get("three_pct"),
                        "FT%": sel_row.get("ft_pct"),
                    }
                ]
            )
            st.dataframe(stats_preview, width="stretch", hide_index=True)

        with auto_col:
            st.markdown("**Automatic roster assist**")
            if hoopr_error:
                st.info(
                    "Auto roster matching is optional. The reliable path is to verify from NCAA / ESPN and apply the stat line below."
                )
                if HAVE_HOOPR:
                    st.caption(f"sportsdataverse could not load cleanly: {hoopr_error}")
                else:
                    st.caption("sportsdataverse is not installed in this environment.")
            elif school:
                if st.button(f"Try auto roster lookup for {school}", key="rec_enrich_btn", width="stretch"):
                    with st.spinner(f"Searching NCAA/ESPN roster data for {school}..."):
                        result = lookup_player_stats_hoopr(school)
                        time.sleep(0.5)

                    if result is not None and len(result) > 0:
                        st.success(f"Found {len(result)} player records at {school}.")
                        st.dataframe(
                            result[["athlete_display_name", "position", "pts", "reb", "ast", "fg_pct"]].head(15)
                            if all(c in result.columns for c in ["athlete_display_name", "pts", "reb", "ast", "fg_pct"])
                            else result.head(15),
                            width="stretch",
                            hide_index=True,
                        )
                        if "athlete_display_name" in result.columns:
                            athlete_options = _best_candidate_labels(result, sel_row) or result["athlete_display_name"].dropna().astype(str).tolist()
                            if athlete_options:
                                athlete_pick = st.selectbox(
                                    "Match this verified stat line to your prospect",
                                    athlete_options,
                                    key=f"rec_match_{sel_prospect}",
                                )
                                st.caption("WAIMS ranks likely matches using non-identifying fields like position and class. You still confirm the final match.")
                                if st.button(f"Apply matched stat line to {sel_prospect}", key=f"rec_apply_{sel_prospect}", width="stretch"):
                                    chosen = result[result["athlete_display_name"].astype(str) == athlete_pick].iloc[0]
                                    updates = {
                                        "ppg": _candidate_value(chosen, ["pts", "ppg"]),
                                        "rpg": _candidate_value(chosen, ["reb", "rpg"]),
                                        "apg": _candidate_value(chosen, ["ast", "apg"]),
                                        "fg_pct": _candidate_value(chosen, ["fg_pct"]),
                                        "three_pct": _candidate_value(chosen, ["fg3_pct", "fg3pt_pct", "three_pct"]),
                                        "ft_pct": _candidate_value(chosen, ["ft_pct"]),
                                    }
                                    df = _apply_verified_stats_to_board(
                                        df,
                                        sel_prospect,
                                        updates,
                                        source_label="Auto roster match (ESPN / NCAA)",
                                        player_label=athlete_pick,
                                    )
                                    st.session_state["recruiting_board_df"] = _persistable_board(df).copy()
                                    _persist_board(_persistable_board(df))
                                    st.success(f"Applied verified stats from {athlete_pick} to {sel_prospect}.")
                                    st.rerun()
                    else:
                        st.warning("No automatic roster match was found. Use the manual verified stat form below instead.")
            else:
                st.info("Add a school name to this prospect to unlock auto roster lookup.")

        with st.form(f"manual_verified_stats_{sel_prospect}"):
            st.markdown("**Manual verified stat line**")
            st.caption(
                "This is the reliable path: verify the prospect on an official NCAA, ESPN, NJCAA, or school source, then apply the stat line here."
            )
            m1, m2 = st.columns(2)
            with m1:
                verified_source = st.selectbox(
                    "Verified source",
                    VERIFIED_SOURCE_OPTIONS,
                    index=0,
                    key=f"verified_source_{sel_prospect}",
                )
                verified_url = st.text_input(
                    "Source URL (optional)",
                    value=str(sel_row.get("verified_url") or ""),
                    key=f"verified_url_{sel_prospect}",
                )
                ppg_val = st.number_input(
                    "PPG",
                    min_value=0.0,
                    max_value=99.9,
                    value=float(_safe_float(sel_row.get("ppg")) or 0.0),
                    step=0.1,
                    key=f"verified_ppg_{sel_prospect}",
                )
                rpg_val = st.number_input(
                    "RPG",
                    min_value=0.0,
                    max_value=99.9,
                    value=float(_safe_float(sel_row.get("rpg")) or 0.0),
                    step=0.1,
                    key=f"verified_rpg_{sel_prospect}",
                )
                apg_val = st.number_input(
                    "APG",
                    min_value=0.0,
                    max_value=99.9,
                    value=float(_safe_float(sel_row.get("apg")) or 0.0),
                    step=0.1,
                    key=f"verified_apg_{sel_prospect}",
                )
            with m2:
                matched_label = st.text_input(
                    "Matched player label (optional)",
                    value=str(sel_row.get("verified_player_label") or ""),
                    key=f"verified_label_{sel_prospect}",
                )
                fg_pct_val = st.number_input(
                    "FG% (decimal)",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(_safe_float(sel_row.get("fg_pct")) or 0.0),
                    step=0.01,
                    key=f"verified_fg_{sel_prospect}",
                )
                three_pct_val = st.number_input(
                    "3PT% (decimal)",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(_safe_float(sel_row.get("three_pct")) or 0.0),
                    step=0.01,
                    key=f"verified_three_{sel_prospect}",
                )
                ft_pct_val = st.number_input(
                    "FT% (decimal)",
                    min_value=0.0,
                    max_value=1.0,
                    value=float(_safe_float(sel_row.get("ft_pct")) or 0.0),
                    step=0.01,
                    key=f"verified_ft_{sel_prospect}",
                )
            apply_manual = st.form_submit_button(f"Apply verified stat line to {sel_prospect}", width="stretch")

        if apply_manual:
            updates = {
                "ppg": ppg_val,
                "rpg": rpg_val,
                "apg": apg_val,
                "fg_pct": fg_pct_val,
                "three_pct": three_pct_val,
                "ft_pct": ft_pct_val,
            }
            df = _apply_verified_stats_to_board(
                df,
                sel_prospect,
                updates,
                source_label=verified_source,
                source_url=verified_url,
                player_label=matched_label,
            )
            st.session_state["recruiting_board_df"] = _persistable_board(df).copy()
            _persist_board(_persistable_board(df))
            st.success(f"Saved verified NCAA/ESPN stat line for {sel_prospect}.")
            st.rerun()

    # ── Export ──
    st.divider()
    st.subheader("Export")

    export_cols = [
        "prospect_code", "position", "class_year", "current_school",
        "prospect_score", "confidence", "contact_stage",
        "ppg", "rpg", "apg", "fg_pct", "staff_grade", "fit_score", "notes",
    ]
    export_df = filtered[[c for c in export_cols if c in filtered.columns]].copy()

    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        st.download_button(
            "⬇ Export board (CSV)",
            data=export_df.to_csv(index=False),
            file_name="waims_prospect_board.csv",
            mime="text/csv",
            width="stretch",
        )
    with col_ex2:
        _download_excel_button(
            "⬇ Export board (Excel)",
            file_name="waims_prospect_board.xlsx",
            frame_map={"Prospect Board": export_df},
            key="download_prospect_board_xlsx",
        )

    st.caption(
        "All exports contain only anonymized codes. No real names or personal "
        "identifiers are stored or transmitted by WAIMS."
    )


# ── STANDALONE TEST ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title="WAIMS GM — Recruiting",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    recruiting_tab()
