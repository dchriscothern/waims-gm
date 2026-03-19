"""Compatibility router for code that still imports app.routes.evaluate.

app.main owns the live endpoint implementation.
"""

from fastapi import APIRouter

from app.main import (
    EvaluateAndSaveOut,
    EvaluateAndSaveRequest,
    EvaluationOut,
    EvaluateRequest,
    evaluate,
    evaluate_and_save,
)

router = APIRouter()
router.add_api_route("/evaluate", evaluate, methods=["POST"], response_model=EvaluationOut)
router.add_api_route(
    "/evaluate-and-save",
    evaluate_and_save,
    methods=["POST"],
    response_model=EvaluateAndSaveOut,
)
