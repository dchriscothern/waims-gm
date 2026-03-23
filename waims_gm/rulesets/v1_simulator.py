"""Compatibility wrapper for older ruleset imports.

The live scoring implementation now lives in waims_gm.services.
"""

from __future__ import annotations

from ..domain import Player, Scorecard, TeamContext
from ..services import evaluate_single_player as _live_evaluate_single_player


def evaluate_player_v1(player: Player, ctx: TeamContext) -> Scorecard:
    return _live_evaluate_single_player(player, ctx)
