"""Compatibility router for code that still imports app.routes.health.

app.main owns the live endpoint implementation.
"""

from fastapi import APIRouter

from app.main import health

router = APIRouter()
router.add_api_route("/health", health, methods=["GET"])
