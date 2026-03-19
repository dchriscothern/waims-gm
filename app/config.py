from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()


def _normalized_env_name(raw_value: str) -> str:
    value = (raw_value or "").strip().lower()
    return value if value in {"sandbox", "live"} else "sandbox"


WAIMS_ENV = _normalized_env_name(os.getenv("WAIMS_ENV", "sandbox"))
IS_LIVE_ENV = WAIMS_ENV == "live"
WAIMS_ENV_LABEL = os.getenv("WAIMS_ENV_LABEL", "Live" if IS_LIVE_ENV else "Sandbox").strip() or (
    "Live" if IS_LIVE_ENV else "Sandbox"
)
API_HOSTPORT = os.getenv("API_HOSTPORT", "").strip()
API_SCHEME = os.getenv("API_SCHEME", "http").strip() or "http"
API_BASE_URL = os.getenv("API_BASE_URL", "").strip().rstrip("/")
if not API_BASE_URL:
    API_BASE_URL = f"{API_SCHEME}://{API_HOSTPORT}".rstrip("/") if API_HOSTPORT else "http://127.0.0.1:8000"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_AUD = os.getenv("SUPABASE_JWT_AUD", "authenticated")
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""


def validate_runtime_settings() -> Dict[str, List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    if not API_BASE_URL.startswith(("http://", "https://")):
        errors.append("API_BASE_URL must start with http:// or https://.")

    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is required.")
    elif not SUPABASE_URL.startswith("https://"):
        errors.append("SUPABASE_URL should start with https://.")
    elif "your-project" in SUPABASE_URL or "your-sandbox-project" in SUPABASE_URL or "your-live-project" in SUPABASE_URL:
        errors.append("SUPABASE_URL is still set to an example placeholder value.")

    if not SUPABASE_ANON_KEY:
        errors.append("SUPABASE_ANON_KEY is required.")
    elif SUPABASE_ANON_KEY.startswith("your-"):
        errors.append("SUPABASE_ANON_KEY is still set to an example placeholder value.")

    label_lower = WAIMS_ENV_LABEL.lower()
    api_lower = API_BASE_URL.lower()

    if IS_LIVE_ENV and ("127.0.0.1" in api_lower or "localhost" in api_lower):
        errors.append("Live environment cannot point API_BASE_URL at localhost.")
    if IS_LIVE_ENV and "sandbox" in label_lower:
        warnings.append("WAIMS_ENV is live but WAIMS_ENV_LABEL still says sandbox.")
    if not IS_LIVE_ENV and "live" in label_lower:
        warnings.append("WAIMS_ENV is sandbox but WAIMS_ENV_LABEL still says live.")
    if not IS_LIVE_ENV and ("127.0.0.1" not in api_lower and "localhost" not in api_lower):
        warnings.append("Sandbox environment is using a non-local API_BASE_URL.")

    return {"errors": errors, "warnings": warnings}
