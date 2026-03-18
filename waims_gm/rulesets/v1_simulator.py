from __future__ import annotations

from ..domain import EvaluationScorecard, Player, TeamContext


def evaluate_player_v1(player: Player, ctx: TeamContext) -> EvaluationScorecard:
    # v1: simple, transparent weighted score. Keep it explainable.
    weights = {
        "fit": 0.35,
        "impact": 0.30,
        "upside": 0.20,
        "risk_inverse": 0.15,
    }

    fit = float(ctx.needs_by_position.get(player.position, 0.5))
    impact = float((player.offense_rating + player.defense_rating) / 2.0)
    upside = float(player.upside)
    risk_inverse = float(1.0 - player.health_risk)

    overall = (
        weights["fit"] * fit
        + weights["impact"] * impact
        + weights["upside"] * upside
        + weights["risk_inverse"] * risk_inverse
    )

    # v1 action policy (placeholder but sensible):
    # - Draft if upside is high or fit is urgent.
    # - Sign if impact is high and risk isn't awful.
    # - Otherwise pass.
    if upside >= 0.70 or fit >= 0.75:
        action = "draft"
    elif impact >= 0.65 and risk_inverse >= 0.55:
        action = "sign"
    else:
        action = "pass"

    tensions: list[str] = []
    if player.upside >= 0.70 and player.minutes_stability < 0.45:
        tensions.append("High upside but uncertain role/minutes stability.")
    if player.health_risk >= 0.60:
        tensions.append("Elevated health risk vs safer alternatives.")
    if fit < 0.35 and impact > 0.70:
        tensions.append("Strong player, but weak positional need fit (BPA vs fit).")

    assumptions = {
        "minutes_assumption": "Assume rotation role; adjust once depth chart is known.",
        "cost_band": f"Tier {player.expected_cost_tier} (v1 heuristic)",
    }

    components = {
        "fit": fit,
        "impact": impact,
        "upside": upside,
        "risk_inverse": risk_inverse,
    }

    return EvaluationScorecard(
        player=player,
        overall_score=overall,
        components=components,
        assumptions=assumptions,
        tension_points=tensions,
        recommended_action=action,
    )