from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv

ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ROOT_ENV)


def fetch_access_token(email: str, password: str) -> str:
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/auth/v1/token?grant_type=password"
    headers = {
        "apikey": os.environ["SUPABASE_ANON_KEY"],
        "Content-Type": "application/json",
    }
    response = httpx.post(
        url,
        headers=headers,
        json={"email": email, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("No access_token returned from Supabase.")
    return token


def api_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def list_evaluations(token: str) -> List[Dict[str, Any]]:
    with httpx.Client(timeout=30) as client:
        response = client.get(
            f"{get_api_base_url()}/evaluations",
            headers=api_headers(token),
        )
        response.raise_for_status()
        return response.json()


def delete_evaluation(token: str, evaluation_id: str) -> None:
    with httpx.Client(timeout=30) as client:
        response = client.delete(
            f"{get_api_base_url()}/evaluations/{evaluation_id}",
            headers=api_headers(token),
        )
        response.raise_for_status()


def create_evaluation(token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{get_api_base_url()}/evaluate-and-save",
            headers=api_headers(token),
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def demo_payloads() -> List[Dict[str, Any]]:
    return [
        {
            "player": {
                "id": "demo_d2_need_guard",
                "name": "Ari Benton",
                "position": "G",
                "age": 22,
                "offense_rating": 74.0,
                "defense_rating": 77.0,
                "shooting_rating": 72.0,
                "playmaking_rating": 70.0,
                "rebounding_rating": 39.0,
                "health_risk": 0.12,
                "upside": 0.69,
                "minutes_stability": 0.84,
                "expected_cost_tier": 1,
            },
            "ctx": {
                "team_id": "sandbox-demo",
                "timeline": "balanced",
                "needs_by_position": {"G": 0.88, "F": 0.42, "C": 0.24},
                "cap_flexibility": 0.44,
                "risk_tolerance": 0.36,
            },
            "display_name": "WAIMS Demo",
            "summary_note": "[DEMO] Ready guard who solves immediate minutes and ball-security needs for a lower-resource staff.",
            "strengths": "Point-of-attack defense\nLive-dribble decision making\nLow-cost rotation fit",
            "concerns": "Limited size\nNot a pure scoring creator",
            "mode": "cbb_d2_low_resource",
        },
        {
            "player": {
                "id": "demo_d2_upside_wing",
                "name": "Malik Stokes",
                "position": "F",
                "age": 19,
                "offense_rating": 71.0,
                "defense_rating": 68.0,
                "shooting_rating": 74.0,
                "playmaking_rating": 58.0,
                "rebounding_rating": 64.0,
                "health_risk": 0.16,
                "upside": 0.88,
                "minutes_stability": 0.58,
                "expected_cost_tier": 2,
            },
            "ctx": {
                "team_id": "sandbox-demo",
                "timeline": "balanced",
                "needs_by_position": {"G": 0.88, "F": 0.42, "C": 0.24},
                "cap_flexibility": 0.44,
                "risk_tolerance": 0.36,
            },
            "display_name": "WAIMS Demo",
            "summary_note": "[DEMO] Younger wing with real growth runway, but less certainty if the question is immediate rotation help.",
            "strengths": "Shotmaking upside\nLength and rebounding tools\nLong-term development ceiling",
            "concerns": "Lower current readiness\nMore projection risk\nHigher acquisition uncertainty",
            "mode": "cbb_d2_low_resource",
        },
        {
            "player": {
                "id": "demo_recruiting_long_wing",
                "name": "Jalen Mercer",
                "position": "F",
                "age": 18,
                "offense_rating": 68.0,
                "defense_rating": 66.0,
                "shooting_rating": 73.0,
                "playmaking_rating": 61.0,
                "rebounding_rating": 56.0,
                "health_risk": 0.08,
                "upside": 0.93,
                "minutes_stability": 0.46,
                "expected_cost_tier": 2,
            },
            "ctx": {
                "team_id": "sandbox-demo",
                "timeline": "rebuild",
                "needs_by_position": {"G": 0.32, "F": 0.77, "C": 0.28},
                "cap_flexibility": 0.58,
                "risk_tolerance": 0.54,
            },
            "display_name": "WAIMS Demo",
            "summary_note": "[DEMO] Long-horizon recruiting target with future-oriented shotmaking and frame-based upside.",
            "strengths": "Development runway\nProjectable jumper\nAge-adjusted upside signal",
            "concerns": "Needs strength\nNot ready for immediate high-usage role",
            "mode": "recruiting_only",
        },
        {
            "player": {
                "id": "demo_high_major_portal_guard",
                "name": "Tori Gaines",
                "position": "G",
                "age": 24,
                "offense_rating": 80.0,
                "defense_rating": 70.0,
                "shooting_rating": 78.0,
                "playmaking_rating": 76.0,
                "rebounding_rating": 35.0,
                "health_risk": 0.14,
                "upside": 0.71,
                "minutes_stability": 0.82,
                "expected_cost_tier": 3,
            },
            "ctx": {
                "team_id": "sandbox-demo",
                "timeline": "win_now",
                "needs_by_position": {"G": 0.84, "F": 0.38, "C": 0.20},
                "cap_flexibility": 0.48,
                "risk_tolerance": 0.34,
            },
            "display_name": "WAIMS Demo",
            "summary_note": "[DEMO] High-major portal guard with immediate usage value and a clean ball-screen translation profile.",
            "strengths": "Immediate scoring gravity\nBall-screen command\nOlder, more stable role projection",
            "concerns": "More expensive add\nLess future growth than younger targets",
            "mode": "cbb_high_major",
        },
    ]


def print_demo_catalog() -> None:
    print("WAIMS-GM demo file set")
    print("")
    for payload in demo_payloads():
        player = payload["player"]
        ctx = payload["ctx"]
        print(
            f"- {player['name']} | {payload['mode']} | {player['position']} | "
            f"age {player['age']} | team {ctx['team_id']} | id {player['id']}"
        )


def normalize_selectors(values: List[str]) -> List[str]:
    selectors: List[str] = []
    for value in values:
        selectors.extend(part.strip() for part in value.split(",") if part.strip())
    return selectors


def select_demo_payloads(requested: List[str]) -> List[Dict[str, Any]]:
    payloads = demo_payloads()
    if not requested:
        return payloads

    selectors = {item.casefold() for item in normalize_selectors(requested)}
    selected: List[Dict[str, Any]] = []

    for payload in payloads:
        player = payload["player"]
        keys = {
            player["id"].casefold(),
            player["name"].casefold(),
        }
        if keys & selectors:
            selected.append(payload)

    if selected:
        return selected

    available = ", ".join(
        f"{payload['player']['name']} ({payload['player']['id']})"
        for payload in payloads
    )
    raise SystemExit(f"No demo files matched --only. Available options: {available}")


def print_seed_summary(
    created_names: List[str],
    replaced_names: List[str],
    skipped_names: List[str],
    dry_run: bool,
) -> None:
    print("")
    if dry_run:
        print("Dry run complete.")
    else:
        print("Seed complete.")
    print(f"Created: {len(created_names)}")
    print(f"Replaced: {len(replaced_names)}")
    print(f"Skipped: {len(skipped_names)}")

    if created_names:
        print("")
        print("Created files:")
        for name in created_names:
            print(f"- {name}")

    if replaced_names:
        print("")
        print("Replaced files:")
        for name in replaced_names:
            print(f"- {name}")

    if skipped_names:
        print("")
        print("Skipped files:")
        for name in skipped_names:
            print(f"- {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed canonical WAIMS-GM demo evaluations into the current sandbox.")
    parser.add_argument("--email", help="Supabase email. If omitted, prompt interactively.")
    parser.add_argument(
        "--only",
        nargs="+",
        help="Seed only specific demo files by player name or canonical player ID. Accepts multiple values or comma-separated values.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the canonical demo file set and exit without authenticating.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created, replaced, or skipped without writing to the API.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing demo rows with matching player IDs before reseeding.",
    )
    args = parser.parse_args()

    if args.list:
        print_demo_catalog()
        return 0

    selected_payloads = select_demo_payloads(args.only or [])

    email = (args.email or input("Supabase email: ").strip())
    password = getpass.getpass("Supabase password (hidden): ")
    token = fetch_access_token(email, password)

    existing_rows = list_evaluations(token)
    existing_by_player_id = {
        ((row.get("player") or {}).get("id")): row
        for row in existing_rows
        if (row.get("player") or {}).get("id")
    }

    created_names: List[str] = []
    skipped_names: List[str] = []
    replaced_names: List[str] = []

    for payload in selected_payloads:
        player_id = payload["player"]["id"]
        player_name = payload["player"]["name"]
        existing = existing_by_player_id.get(player_id)

        if existing and not args.replace:
            skipped_names.append(player_name)
            print(f"Skip  | {player_name}")
            continue

        if existing and args.replace:
            replaced_names.append(player_name)
            if args.dry_run:
                print(f"Would replace | {player_name}")
            else:
                delete_evaluation(token, existing["id"])
                print(f"Replace | {player_name}")

        if args.dry_run:
            created_names.append(player_name)
            if not existing:
                print(f"Would create  | {player_name}")
            continue

        result = create_evaluation(token, payload)
        created_names.append(player_name)
        print(f"Create | {player_name} ({result.get('evaluation_id')})")

    print_seed_summary(created_names, replaced_names, skipped_names, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
