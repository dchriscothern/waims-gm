from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv
from waims_gm.demo_data import demo_payloads

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
