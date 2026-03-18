from __future__ import annotations

from ..domain import EvaluationScorecard, Player, TeamContext
from ..rulesets.v1_simulator import evaluate_player_v1


def evaluate_single_player(player: Player, ctx: TeamContext) -> EvaluationScorecard:
    return evaluate_player_v1(player, ctx)