from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


Timeline = Literal["win_now", "balanced", "rebuild"]
Action = Literal["draft", "sign", "pass"]


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    position: str  # e.g. "G", "F", "C"
    age: int

    offense_rating: float  # 0..1
    defense_rating: float  # 0..1
    shooting_rating: float  # 0..1
    playmaking_rating: float  # 0..1
    rebounding_rating: float  # 0..1

    health_risk: float  # 0..1 (higher = worse)
    upside: float  # 0..1
    minutes_stability: float  # 0..1 (higher = more stable role/minutes)

    expected_cost_tier: int  # 1..5 (v1 heuristic)


@dataclass(frozen=True)
class TeamContext:
    gm_id: str
    team_id: str
    timeline: Timeline

    needs_by_position: Dict[str, float]  # 0..1 per position
    cap_flexibility: float  # 0..1
    risk_tolerance: float  # 0..1
    mode: Optional[str] = None


@dataclass
class Scorecard:
    player: Player
    overall_score: float
    components: Dict[str, float]
    assumptions: Dict[str, str]
    tension_points: List[str]
    recommended_action: Action
    runner_up_reason: Optional[str] = None


# Backward-compatible alias for older imports.
EvaluationScorecard = Scorecard
