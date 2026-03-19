"""Compatibility exports for code that still imports from app.services.supabase.

app.main is the single source of truth for the live persistence path.
"""

from app.main import insert_evaluation, sb_headers, upsert_gm_profile

__all__ = ["insert_evaluation", "sb_headers", "upsert_gm_profile"]
