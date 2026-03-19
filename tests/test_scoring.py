import unittest

from waims_gm.domain import Player, TeamContext
from waims_gm.services import evaluate_single_player, get_mode_weights


COMPONENT_KEYS = {"fit", "impact", "upside", "availability", "value"}
MODES = (
    "pro_wnba",
    "cbb_high_major",
    "cbb_d2_low_resource",
    "recruiting_only",
)


def make_player(**overrides):
    data = {
        "id": "p1",
        "name": "Sample Player",
        "position": "G",
        "age": 21,
        "offense_rating": 72.0,
        "defense_rating": 64.0,
        "shooting_rating": 68.0,
        "playmaking_rating": 70.0,
        "rebounding_rating": 38.0,
        "health_risk": 0.18,
        "upside": 0.78,
        "minutes_stability": 0.68,
        "expected_cost_tier": 3,
    }
    data.update(overrides)
    return Player(**data)


def make_context(mode, **overrides):
    data = {
        "gm_id": "gm-1",
        "team_id": "team-1",
        "timeline": "balanced",
        "needs_by_position": {"G": 0.75, "F": 0.45, "C": 0.25},
        "cap_flexibility": 0.55,
        "risk_tolerance": 0.4,
        "mode": mode,
    }
    data.update(overrides)
    return TeamContext(**data)


class ScoringTests(unittest.TestCase):
    def test_mode_weights_are_complete_and_normalized(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                weights = get_mode_weights(mode)
                self.assertEqual(set(weights), COMPONENT_KEYS)
                self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_evaluation_returns_expected_component_schema(self):
        scorecard = evaluate_single_player(
            make_player(),
            make_context("pro_wnba"),
        )

        self.assertEqual(set(scorecard.components), COMPONENT_KEYS)
        self.assertGreaterEqual(scorecard.overall_score, 0.0)
        self.assertLessEqual(scorecard.overall_score, 100.0)
        self.assertIn(scorecard.recommended_action, {"draft", "sign", "pass"})

        for name, value in scorecard.components.items():
            with self.subTest(component=name):
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 100.0)

    def test_recruiting_mode_rewards_upside_more_than_pro(self):
        player = make_player(
            offense_rating=67.0,
            defense_rating=57.0,
            shooting_rating=69.0,
            playmaking_rating=71.0,
            rebounding_rating=32.0,
            health_risk=0.21,
            upside=0.95,
            minutes_stability=0.42,
            expected_cost_tier=2,
        )

        pro_score = evaluate_single_player(player, make_context("pro_wnba"))
        recruiting_score = evaluate_single_player(player, make_context("recruiting_only"))

        self.assertGreater(recruiting_score.overall_score, pro_score.overall_score)

    def test_d2_mode_rewards_low_cost_fit_more_than_high_major(self):
        player = make_player(
            position="F",
            offense_rating=66.0,
            defense_rating=72.0,
            shooting_rating=70.0,
            playmaking_rating=52.0,
            rebounding_rating=69.0,
            upside=0.72,
            minutes_stability=0.8,
            expected_cost_tier=1,
        )
        context_overrides = {
            "needs_by_position": {"G": 0.3, "F": 0.9, "C": 0.2},
            "cap_flexibility": 0.42,
            "risk_tolerance": 0.35,
        }

        high_major_score = evaluate_single_player(
            player,
            make_context("cbb_high_major", **context_overrides),
        )
        d2_score = evaluate_single_player(
            player,
            make_context("cbb_d2_low_resource", **context_overrides),
        )

        self.assertGreater(d2_score.overall_score, high_major_score.overall_score)

    def test_d2_mode_prefers_ready_low_cost_contributor_over_raw_upside_case(self):
        ready_player = make_player(
            name="Ready Wing",
            position="F",
            age=22,
            offense_rating=68.0,
            defense_rating=74.0,
            shooting_rating=71.0,
            playmaking_rating=54.0,
            rebounding_rating=69.0,
            health_risk=0.14,
            upside=0.66,
            minutes_stability=0.84,
            expected_cost_tier=1,
        )
        upside_player = make_player(
            name="Raw Guard",
            position="G",
            age=18,
            offense_rating=70.0,
            defense_rating=58.0,
            shooting_rating=72.0,
            playmaking_rating=74.0,
            rebounding_rating=36.0,
            health_risk=0.12,
            upside=0.93,
            minutes_stability=0.46,
            expected_cost_tier=2,
        )
        ready_ctx = make_context(
            "cbb_d2_low_resource",
            needs_by_position={"G": 0.8, "F": 0.75, "C": 0.25},
            cap_flexibility=0.45,
            risk_tolerance=0.38,
        )
        upside_ctx = make_context(
            "cbb_d2_low_resource",
            needs_by_position={"G": 0.8, "F": 0.75, "C": 0.25},
            cap_flexibility=0.45,
            risk_tolerance=0.38,
        )

        ready_score = evaluate_single_player(ready_player, ready_ctx)
        upside_score = evaluate_single_player(upside_player, upside_ctx)

        self.assertEqual(ready_score.recommended_action, "draft")
        self.assertNotEqual(upside_score.recommended_action, "draft")
        self.assertGreater(ready_score.components["value"], upside_score.components["value"])

    def test_pro_mode_rewards_established_impact_more_than_recruiting(self):
        player = make_player(
            age=27,
            offense_rating=84.0,
            defense_rating=79.0,
            shooting_rating=81.0,
            playmaking_rating=74.0,
            rebounding_rating=58.0,
            health_risk=0.08,
            upside=0.61,
            minutes_stability=0.9,
            expected_cost_tier=4,
        )

        pro_score = evaluate_single_player(player, make_context("pro_wnba"))
        recruiting_score = evaluate_single_player(player, make_context("recruiting_only"))

        self.assertGreater(pro_score.overall_score, recruiting_score.overall_score)

    def test_recruiting_mode_rewards_younger_profile_when_skill_band_is_similar(self):
        younger_player = make_player(
            age=18,
            offense_rating=69.0,
            defense_rating=61.0,
            shooting_rating=71.0,
            playmaking_rating=72.0,
            rebounding_rating=35.0,
            health_risk=0.13,
            upside=0.82,
            minutes_stability=0.5,
            expected_cost_tier=2,
        )
        older_player = make_player(
            age=24,
            offense_rating=69.0,
            defense_rating=61.0,
            shooting_rating=71.0,
            playmaking_rating=72.0,
            rebounding_rating=35.0,
            health_risk=0.13,
            upside=0.82,
            minutes_stability=0.5,
            expected_cost_tier=2,
        )

        younger_score = evaluate_single_player(younger_player, make_context("recruiting_only"))
        older_score = evaluate_single_player(older_player, make_context("recruiting_only"))

        self.assertGreater(younger_score.components["upside"], older_score.components["upside"])
        self.assertGreater(younger_score.overall_score, older_score.overall_score)


if __name__ == "__main__":
    unittest.main()
