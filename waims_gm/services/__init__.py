from __future__ import annotations

from typing import Dict, List

from waims_gm.domain import Player, TeamContext, Scorecard


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def scale_0_1_to_100(value: float) -> float:
    return clamp(value, 0.0, 1.0) * 100.0


def normalize_cost_tier(cost_tier: int) -> float:
    return clamp(100.0 - (float(cost_tier) * 10.0), 0.0, 100.0)


def compute_position_fit(player: Player, ctx: TeamContext) -> float:
    raw_need = ctx.needs_by_position.get(player.position, 0.5)
    return scale_0_1_to_100(raw_need)


def compute_impact_score(player: Player) -> float:
    return (
        player.offense_rating * 0.28
        + player.defense_rating * 0.24
        + player.shooting_rating * 0.18
        + player.playmaking_rating * 0.18
        + player.rebounding_rating * 0.12
    )


def compute_upside_score(player: Player) -> float:
    return scale_0_1_to_100(player.upside)


def compute_availability_score(player: Player) -> float:
    risk_inverse = scale_0_1_to_100(1.0 - player.health_risk)
    minutes_score = scale_0_1_to_100(player.minutes_stability)
    return risk_inverse * 0.55 + minutes_score * 0.45


def compute_contextual_value_score(player: Player, ctx: TeamContext) -> float:
    cost_score = normalize_cost_tier(player.expected_cost_tier)
    fit_score = compute_position_fit(player, ctx)
    cap_score = scale_0_1_to_100(ctx.cap_flexibility)
    risk_env_score = scale_0_1_to_100(ctx.risk_tolerance)

    return (
        cost_score * 0.35
        + fit_score * 0.35
        + cap_score * 0.15
        + risk_env_score * 0.15
    )


def compute_recruiting_upside_score(player: Player) -> float:
    base_upside = compute_upside_score(player)
    age_bonus = clamp((21.0 - float(player.age)) * 4.5, -18.0, 18.0)
    return clamp(base_upside + age_bonus, 0.0, 100.0)


def compute_d2_value_score(player: Player, ctx: TeamContext, base_value_score: float) -> float:
    availability_score = compute_availability_score(player)
    readiness_age_score = clamp(100.0 - (abs(float(player.age) - 21.0) * 8.0), 55.0, 100.0)
    return clamp(
        base_value_score * 0.72
        + availability_score * 0.18
        + readiness_age_score * 0.10,
        0.0,
        100.0,
    )


def compute_recruiting_value_score(player: Player, ctx: TeamContext, base_value_score: float) -> float:
    fit_score = compute_position_fit(player, ctx)
    recruiting_upside = compute_recruiting_upside_score(player)
    return clamp(
        base_value_score * 0.45
        + recruiting_upside * 0.35
        + fit_score * 0.20,
        0.0,
        100.0,
    )


def infer_mode_from_context(ctx: TeamContext) -> str:
    return getattr(ctx, "mode", "pro_wnba")


def get_mode_weights(mode: str) -> Dict[str, float]:
    mode = mode or "pro_wnba"

    if mode == "cbb_high_major":
        return {
            "fit": 0.20,
            "impact": 0.28,
            "upside": 0.20,
            "availability": 0.14,
            "value": 0.18,
        }

    if mode == "cbb_d2_low_resource":
        return {
            "fit": 0.24,
            "impact": 0.22,
            "upside": 0.14,
            "availability": 0.18,
            "value": 0.22,
        }

    if mode == "recruiting_only":
        return {
            "fit": 0.16,
            "impact": 0.18,
            "upside": 0.32,
            "availability": 0.10,
            "value": 0.24,
        }

    return {
        "fit": 0.18,
        "impact": 0.30,
        "upside": 0.16,
        "availability": 0.18,
        "value": 0.18,
    }


def build_tension_points(
    player: Player,
    ctx: TeamContext,
    fit_score: float,
    impact_score: float,
    upside_score: float,
    availability_score: float,
    value_score: float,
) -> List[str]:
    tensions: List[str] = []

    if player.health_risk >= 0.35:
        tensions.append("Health risk is elevated relative to a stable acquisition profile.")

    if player.minutes_stability <= 0.45:
        tensions.append("Minutes stability is low, which increases role-translation uncertainty.")

    if player.expected_cost_tier >= 4:
        tensions.append("Expected cost tier is high enough to compress surplus value.")

    if fit_score < 45:
        tensions.append("Roster need is not strongly aligned with the player's listed position.")

    if player.shooting_rating < 60 and player.offense_rating >= 72:
        tensions.append("Overall offensive value may outpace shooting portability.")

    if player.playmaking_rating < 50 and player.position == "G":
        tensions.append("Lead-guard archetype concerns: playmaking does not currently anchor the profile.")

    if player.rebounding_rating < 45 and player.position in {"F", "C"}:
        tensions.append("Frontcourt rebounding profile may be light for the listed position.")

    if upside_score >= 75 and availability_score < 60:
        tensions.append("Long-term upside is attractive, but near-term dependability is less stable.")

    if impact_score >= 74 and value_score < 55:
        tensions.append("Player impact appears stronger than value-to-cost efficiency.")

    if scale_0_1_to_100(ctx.risk_tolerance) < 40 and player.health_risk > 0.25:
        tensions.append("Team risk environment appears conservative relative to the player's risk profile.")

    return tensions


def build_assumptions(player: Player) -> Dict[str, str]:
    if player.minutes_stability >= 0.75:
        minutes_assumption = "Assume stable rotation role with relatively clear minute continuity."
    elif player.minutes_stability >= 0.50:
        minutes_assumption = "Assume rotation role; adjust once depth chart is known."
    else:
        minutes_assumption = "Assume volatile role/minutes until lineup and usage context are clarified."

    if player.expected_cost_tier <= 1:
        cost_band = "Tier 0-1 (low-cost acquisition profile)"
    elif player.expected_cost_tier <= 3:
        cost_band = "Tier 2-3 (moderate acquisition profile)"
    else:
        cost_band = "Tier 4+ (premium acquisition profile)"

    return {
        "minutes_assumption": minutes_assumption,
        "cost_band": cost_band,
    }


def choose_recommendation(
    overall_score: float,
    fit_score: float,
    impact_score: float,
    upside_score: float,
    availability_score: float,
    value_score: float,
    tensions: List[str],
    mode: str,
) -> str:
    major_tension_count = len(tensions)

    if mode == "recruiting_only":
        if overall_score >= 74 and upside_score >= 82 and major_tension_count <= 3:
            return "draft"
        if overall_score >= 62 and upside_score >= 65:
            return "sign"
        return "pass"

    if mode == "cbb_d2_low_resource":
        if (
            overall_score >= 72
            and value_score >= 68
            and fit_score >= 55
            and availability_score >= 72
            and impact_score >= 66
            and major_tension_count <= 3
        ):
            return "draft"
        if overall_score >= 60 and value_score >= 55:
            return "sign"
        return "pass"

    if mode == "cbb_high_major":
        if overall_score >= 74 and impact_score >= 70 and fit_score >= 55 and major_tension_count <= 3:
            return "draft"
        if overall_score >= 63 and impact_score >= 62:
            return "sign"
        return "pass"

    if overall_score >= 73 and impact_score >= 68 and availability_score >= 60 and major_tension_count <= 3:
        return "draft"
    if overall_score >= 62 and impact_score >= 60:
        return "sign"
    return "pass"


def evaluate_single_player(player: Player, ctx: TeamContext) -> Scorecard:
    mode = infer_mode_from_context(ctx)
    weights = get_mode_weights(mode)

    fit_score = compute_position_fit(player, ctx)
    impact_score = compute_impact_score(player)
    availability_score = compute_availability_score(player)
    base_upside_score = compute_upside_score(player)
    base_value_score = compute_contextual_value_score(player, ctx)

    upside_score = base_upside_score
    value_score = base_value_score
    if mode == "recruiting_only":
        upside_score = compute_recruiting_upside_score(player)
        value_score = compute_recruiting_value_score(player, ctx, base_value_score)
    elif mode == "cbb_d2_low_resource":
        value_score = compute_d2_value_score(player, ctx, base_value_score)

    overall_score = (
        fit_score * weights["fit"]
        + impact_score * weights["impact"]
        + upside_score * weights["upside"]
        + availability_score * weights["availability"]
        + value_score * weights["value"]
    )

    overall_score = round(clamp(overall_score, 0.0, 100.0), 2)

    tensions = build_tension_points(
        player=player,
        ctx=ctx,
        fit_score=fit_score,
        impact_score=impact_score,
        upside_score=upside_score,
        availability_score=availability_score,
        value_score=value_score,
    )

    recommendation = choose_recommendation(
        overall_score=overall_score,
        fit_score=fit_score,
        impact_score=impact_score,
        upside_score=upside_score,
        availability_score=availability_score,
        value_score=value_score,
        tensions=tensions,
        mode=mode,
    )

    assumptions = build_assumptions(player)

    components = {
        "fit": round(fit_score, 2),
        "impact": round(impact_score, 2),
        "upside": round(upside_score, 2),
        "availability": round(availability_score, 2),
        "value": round(value_score, 2),
    }

    return Scorecard(
        overall_score=overall_score,
        components=components,
        assumptions=assumptions,
        tension_points=tensions,
        recommended_action=recommendation,
        player=player,
    )
