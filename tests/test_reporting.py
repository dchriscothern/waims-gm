import unittest

from streamlit_app import (
    build_compare_decision_snapshot,
    build_compare_export_markdown,
    build_comparison_verdicts,
    build_decision_lens,
    build_roster_need_call,
)


class ReportingTests(unittest.TestCase):
    def test_build_decision_lens_mentions_strongest_and_weakest_components(self):
        detail = {
            "mode": "cbb_d2_low_resource",
            "recommended_action": "sign",
            "components": {
                "fit": 82.0,
                "impact": 61.0,
                "upside": 68.0,
                "availability": 73.0,
                "value": 79.0,
            },
        }

        lens = build_decision_lens(detail)

        self.assertIn("resource-efficient roster lens", lens)
        self.assertIn("current roster fit", lens)
        self.assertIn("immediate impact", lens)
        self.assertIn("Fit Add", lens)

    def test_build_comparison_verdicts_picks_expected_winners(self):
        left = {
            "mode": "recruiting_only",
            "player": {"name": "Player A"},
            "components": {
                "fit": 74.0,
                "impact": 63.0,
                "upside": 91.0,
                "availability": 58.0,
                "value": 71.0,
            },
        }
        right = {
            "mode": "recruiting_only",
            "player": {"name": "Player B"},
            "components": {
                "fit": 79.0,
                "impact": 66.0,
                "upside": 84.0,
                "availability": 76.0,
                "value": 68.0,
            },
        }

        verdicts = {item["title"]: item for item in build_comparison_verdicts(left, right)}

        self.assertEqual(verdicts["Best long-range target"]["winner"], "Player B")
        self.assertEqual(verdicts["Safer near-term bet"]["winner"], "Player B")
        self.assertEqual(verdicts["Higher long-term upside"]["winner"], "Player A")
        self.assertEqual(verdicts["Better value profile"]["winner"], "Player A")

    def test_build_roster_need_call_prioritizes_positional_need_in_d2_mode(self):
        left = {
            "mode": "cbb_d2_low_resource",
            "ctx": {"needs_by_position": {"G": 0.9, "F": 0.35, "C": 0.2}},
            "player": {"name": "Need Guard", "position": "G"},
            "components": {
                "fit": 73.0,
                "impact": 65.0,
                "upside": 68.0,
                "availability": 79.0,
                "value": 77.0,
            },
        }
        right = {
            "mode": "cbb_d2_low_resource",
            "ctx": {"needs_by_position": {"G": 0.9, "F": 0.35, "C": 0.2}},
            "player": {"name": "Better Forward", "position": "F"},
            "components": {
                "fit": 75.0,
                "impact": 67.0,
                "upside": 69.0,
                "availability": 76.0,
                "value": 74.0,
            },
        }

        verdict = build_roster_need_call(left, right)

        self.assertEqual(verdict["title"], "Roster Need Call")
        self.assertEqual(verdict["winner"], "Need Guard")
        self.assertIn("sharpest current roster need is G", verdict["note"])
        self.assertIn("fit, value, and near-term reliability", verdict["note"])

    def test_build_roster_need_call_prefers_upside_in_recruiting_mode(self):
        left = {
            "mode": "recruiting_only",
            "ctx": {"needs_by_position": {"G": 0.45, "F": 0.5, "C": 0.35}},
            "player": {"name": "Younger Wing", "position": "F"},
            "components": {
                "fit": 72.0,
                "impact": 60.0,
                "upside": 92.0,
                "availability": 57.0,
                "value": 73.0,
            },
        }
        right = {
            "mode": "recruiting_only",
            "ctx": {"needs_by_position": {"G": 0.45, "F": 0.5, "C": 0.35}},
            "player": {"name": "Safer Wing", "position": "F"},
            "components": {
                "fit": 77.0,
                "impact": 66.0,
                "upside": 81.0,
                "availability": 74.0,
                "value": 69.0,
            },
        }

        verdict = build_roster_need_call(left, right)

        self.assertEqual(verdict["title"], "Recruiting Need Call")
        self.assertEqual(verdict["winner"], "Younger Wing")
        self.assertIn("upside, fit, and long-horizon value", verdict["note"])

    def test_build_compare_export_markdown_includes_primary_sections(self):
        left = {
            "mode": "cbb_d2_low_resource",
            "ctx": {"needs_by_position": {"G": 0.82, "F": 0.45, "C": 0.2}},
            "player": {"name": "Need Guard", "position": "G", "age": 22},
            "overall_score": 74.2,
            "recommended_action": "draft",
            "summary_note": "Ready rotation guard for immediate minutes.",
            "strengths": "Point-of-attack defense\nLow-cost fit",
            "concerns": "Limited shot creation",
            "components": {
                "fit": 77.0,
                "impact": 68.0,
                "upside": 66.0,
                "availability": 79.0,
                "value": 81.0,
            },
        }
        right = {
            "mode": "cbb_d2_low_resource",
            "ctx": {"needs_by_position": {"G": 0.82, "F": 0.45, "C": 0.2}},
            "player": {"name": "Scoring Wing", "position": "F", "age": 20},
            "overall_score": 73.4,
            "recommended_action": "sign",
            "summary_note": "More scoring pop, less direct positional need.",
            "strengths": "Shotmaking upside",
            "concerns": "Higher cost tier\nLess role certainty",
            "components": {
                "fit": 74.0,
                "impact": 70.0,
                "upside": 74.0,
                "availability": 71.0,
                "value": 70.0,
            },
        }

        markdown = build_compare_export_markdown(left, right)

        self.assertIn("# Need Guard vs Scoring Wing - WAIMS-GM Comparison Brief", markdown)
        self.assertIn("## Roster Need Call", markdown)
        self.assertIn("## Decision Verdicts", markdown)
        self.assertIn("| Component | Need Guard | Edge | Scoring Wing |", markdown)
        self.assertIn("## Need Guard Snapshot", markdown)
        self.assertIn("## Scoring Wing Snapshot", markdown)

    def test_build_compare_export_markdown_handles_missing_notes(self):
        left = {
            "mode": "pro_wnba",
            "player": {"name": "Player One", "position": "G", "age": 27},
            "overall_score": 78.1,
            "recommended_action": "sign",
            "components": {
                "fit": 76.0,
                "impact": 82.0,
                "upside": 61.0,
                "availability": 80.0,
                "value": 69.0,
            },
        }
        right = {
            "mode": "pro_wnba",
            "player": {"name": "Player Two", "position": "G", "age": 26},
            "overall_score": 77.0,
            "recommended_action": "sign",
            "components": {
                "fit": 75.0,
                "impact": 80.0,
                "upside": 63.0,
                "availability": 79.0,
                "value": 68.0,
            },
        }

        markdown = build_compare_export_markdown(left, right)

        self.assertIn("- Summary Note: No summary note.", markdown)
        self.assertIn("- No strengths entered.", markdown)
        self.assertIn("- No concerns entered.", markdown)

    def test_build_compare_decision_snapshot_surfaces_three_decision_lanes(self):
        left = {
            "mode": "cbb_d2_low_resource",
            "player": {"name": "Need Guard", "position": "G"},
            "components": {
                "fit": 77.0,
                "impact": 68.0,
                "upside": 66.0,
                "availability": 79.0,
                "value": 81.0,
            },
        }
        right = {
            "mode": "cbb_d2_low_resource",
            "player": {"name": "Upside Wing", "position": "F"},
            "components": {
                "fit": 73.0,
                "impact": 66.0,
                "upside": 84.0,
                "availability": 69.0,
                "value": 71.0,
            },
        }

        snapshot = {item["title"]: item for item in build_compare_decision_snapshot(left, right)}

        self.assertEqual(len(snapshot), 3)
        self.assertEqual(snapshot["Best current rotation answer"]["winner"], "Need Guard")
        self.assertEqual(snapshot["Best long-term asset bet"]["winner"], "Upside Wing")
        self.assertEqual(snapshot["Best value decision"]["winner"], "Need Guard")

    def test_build_compare_export_markdown_includes_decision_snapshot(self):
        left = {
            "mode": "recruiting_only",
            "player": {"name": "Younger Wing", "position": "F", "age": 18},
            "overall_score": 75.6,
            "recommended_action": "draft",
            "components": {
                "fit": 72.0,
                "impact": 60.0,
                "upside": 92.0,
                "availability": 57.0,
                "value": 73.0,
            },
        }
        right = {
            "mode": "recruiting_only",
            "player": {"name": "Safer Wing", "position": "F", "age": 21},
            "overall_score": 73.1,
            "recommended_action": "sign",
            "components": {
                "fit": 77.0,
                "impact": 66.0,
                "upside": 81.0,
                "availability": 74.0,
                "value": 69.0,
            },
        }

        markdown = build_compare_export_markdown(left, right)

        self.assertIn("## Decision Snapshot", markdown)
        self.assertIn("Best current rotation answer", markdown)
        self.assertIn("Best long-term asset bet", markdown)
        self.assertIn("Best value decision", markdown)


if __name__ == "__main__":
    unittest.main()
