import unittest

import pandas as pd

from waims_gm_recruiting import (
    STEP_3_HEADER,
    TEMPLATE_COLUMNS_CORE,
    _apply_verified_stats_to_board,
    _best_candidate_labels,
    validate_recruiting_upload,
)


class RecruitingTests(unittest.TestCase):
    def test_core_template_columns_are_short_default(self):
        self.assertEqual(
            TEMPLATE_COLUMNS_CORE,
            [
                "prospect_code",
                "position",
                "class_year",
                "current_school",
                "ppg",
                "rpg",
                "apg",
                "fg_pct",
                "staff_grade",
                "contact_stage",
            ],
        )
        self.assertIn("Pull verified game stats from NCAA", STEP_3_HEADER)

    def test_validate_recruiting_upload_normalizes_common_headers(self):
        raw = pd.DataFrame(
            [
                {
                    "Prospect ID": "pros-001",
                    "Pos": "pg",
                    "Year": "freshman",
                    "School": "Example Community College",
                    "Points Per Game": "18.5",
                }
            ]
        )

        cleaned, errors, warnings = validate_recruiting_upload(raw)

        self.assertEqual(errors, [])
        self.assertEqual(cleaned.loc[0, "prospect_code"], "PROS-001")
        self.assertEqual(cleaned.loc[0, "position"], "PG")
        self.assertEqual(cleaned.loc[0, "class_year"], "FR")
        self.assertAlmostEqual(float(cleaned.loc[0, "ppg"]), 18.5)
        self.assertTrue(any("Normalized incoming column names" in warning for warning in warnings))

    def test_validate_recruiting_upload_rejects_duplicate_codes(self):
        raw = pd.DataFrame(
            [
                {"prospect_code": "PROS-001", "position": "PG", "class_year": "FR", "current_school": "School A"},
                {"prospect_code": "PROS-001", "position": "SG", "class_year": "SO", "current_school": "School B"},
            ]
        )

        _, errors, _ = validate_recruiting_upload(raw)

        self.assertTrue(any("Duplicate prospect code" in error for error in errors))

    def test_best_candidate_labels_prioritizes_position_and_class(self):
        candidates = pd.DataFrame(
            [
                {"athlete_display_name": "Player Big", "position": "C", "class": "SR"},
                {"athlete_display_name": "Player Guard", "position": "PG", "class": "FR"},
                {"athlete_display_name": "Player Wing", "position": "SF", "class": "FR"},
            ]
        )
        prospect = pd.Series({"position": "PG", "class_year": "FR"})

        ranked = _best_candidate_labels(candidates, prospect)

        self.assertEqual(ranked[0], "Player Guard")

    def test_apply_verified_stats_persists_source_metadata(self):
        board = pd.DataFrame(
            [
                {
                    "prospect_code": "PROS-001",
                    "position": "PG",
                    "class_year": "FR",
                    "current_school": "Example Community College",
                    "ppg": None,
                    "rpg": None,
                    "apg": None,
                    "fg_pct": None,
                }
            ]
        )

        updated = _apply_verified_stats_to_board(
            board,
            "PROS-001",
            {"ppg": 18.5, "rpg": 4.2, "apg": 6.1, "fg_pct": 0.47},
            source_label="NCAA player / team page",
            source_url="https://example.com/player",
            player_label="Example Guard",
        )

        self.assertAlmostEqual(float(updated.loc[0, "ppg"]), 18.5)
        self.assertEqual(updated.loc[0, "verified_source"], "NCAA player / team page")
        self.assertEqual(updated.loc[0, "verified_url"], "https://example.com/player")
        self.assertEqual(updated.loc[0, "verified_player_label"], "Example Guard")
        self.assertTrue(str(updated.loc[0, "verified_updated_at"]))


if __name__ == "__main__":
    unittest.main()
