"""Compatibility exports for code that still imports from app.auth.

app.main is the single source of truth for the live auth path.
"""

from app.main import get_current_gm

__all__ = ["get_current_gm"]
