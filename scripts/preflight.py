from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import URLError
from urllib.request import urlopen

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.config import API_BASE_URL, WAIMS_DEMO_MODE, WAIMS_ENV, WAIMS_ENV_LABEL, validate_runtime_settings


def _check_health() -> tuple[bool, str]:
    health_url = f"{API_BASE_URL}/health"
    try:
        with urlopen(health_url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        return False, f"Health check failed for {health_url}: {exc}"
    except Exception as exc:
        return False, f"Could not parse health response from {health_url}: {exc}"

    if not payload.get("ok"):
        return False, f"Health endpoint returned a non-ok payload: {payload}"

    reported_env = payload.get("environment")
    if reported_env and reported_env != WAIMS_ENV:
        return False, f"Health endpoint reports environment '{reported_env}', expected '{WAIMS_ENV}'."

    return True, f"Health check passed for {health_url}."


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WAIMS-GM runtime settings before launch or deploy.")
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Call the configured /health endpoint after validating environment variables.",
    )
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Treat warnings as failures.",
    )
    args = parser.parse_args()

    checks = validate_runtime_settings()
    errors = list(checks["errors"])
    warnings = list(checks["warnings"])

    print("WAIMS-GM Preflight")
    print(f"Environment: {WAIMS_ENV}")
    print(f"Label: {WAIMS_ENV_LABEL}")
    print(f"Demo mode: {'on' if WAIMS_DEMO_MODE else 'off'}")
    print(f"API base URL: {API_BASE_URL}")

    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"- {item}")

    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")

    if args.check_health and not errors:
        ok, message = _check_health()
        print(f"\nHealth: {message}")
        if not ok:
            errors.append(message)

    if errors or (args.strict_warnings and warnings):
        print("\nPreflight status: FAILED")
        return 1

    print("\nPreflight status: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
