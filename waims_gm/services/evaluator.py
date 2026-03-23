"""Compatibility wrapper for older imports.

The package-level waims_gm.services.evaluate_single_player function is the
single source of truth for the live scoring path.
"""

from __future__ import annotations

from ..domain import Player, Scorecard, TeamContext
from . import evaluate_single_player as _live_evaluate_single_player


def evaluate_single_player(player: Player, ctx: TeamContext) -> Scorecard:
    return _live_evaluate_single_player(player, ctx)
