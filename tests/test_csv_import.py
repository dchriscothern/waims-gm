import unittest

from streamlit_app import build_csv_sample_text, build_csv_template_text, parse_csv_import_text, split_csv_duplicates


class CsvImportTests(unittest.TestCase):
    def test_template_includes_expected_headers_only(self):
        template = build_csv_template_text()

        self.assertIn("player_id,player_name,position,age", template)
        self.assertIn("mode", template)
        self.assertNotIn("Ari Benton", template)

    def test_sample_text_includes_ready_rows(self):
        sample = build_csv_sample_text()

        self.assertIn("Ari Benton", sample)
        self.assertIn("Jalen Mercer", sample)

    def test_parse_csv_import_text_uses_default_mode_when_blank(self):
        csv_text = """display_name,player_id,player_name,position,age,offense_rating,defense_rating,shooting_rating,playmaking_rating,rebounding_rating,health_risk,upside,minutes_stability,expected_cost_tier,team_id,timeline,need_g,need_f,need_c,cap_flexibility,risk_tolerance,summary_note,strengths,concerns,mode
Coach Demo,p900,Jordan Hale,G,22,76,68,74,72,40,0.12,0.71,0.83,1,team-x,balanced,0.82,0.35,0.18,0.54,0.38,Steady lead guard,Pick and roll,Size,
"""
        payloads, errors = parse_csv_import_text(csv_text, default_mode="cbb_d2_low_resource")

        self.assertEqual(errors, [])
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["mode"], "cbb_d2_low_resource")
        self.assertEqual(payloads[0]["player"]["name"], "Jordan Hale")

    def test_parse_csv_import_text_reports_invalid_timeline(self):
        csv_text = """display_name,player_id,player_name,position,age,offense_rating,defense_rating,shooting_rating,playmaking_rating,rebounding_rating,health_risk,upside,minutes_stability,expected_cost_tier,team_id,timeline,need_g,need_f,need_c,cap_flexibility,risk_tolerance,summary_note,strengths,concerns,mode
Coach Demo,p901,Riley Stone,F,21,71,75,72,58,65,0.14,0.66,0.79,2,team-y,unknown,0.36,0.78,0.22,0.61,0.42,,Defends spots,Creation ceiling,cbb_high_major
"""
        payloads, errors = parse_csv_import_text(csv_text, default_mode="cbb_high_major")

        self.assertEqual(payloads, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("timeline", errors[0])

    def test_split_csv_duplicates_flags_player_id_plus_team_id(self):
        payloads = [
            {
                "player": {"id": "p900", "name": "Jordan Hale"},
                "ctx": {"team_id": "team-x"},
                "mode": "cbb_d2_low_resource",
            },
            {
                "player": {"id": "p901", "name": "Riley Stone"},
                "ctx": {"team_id": "team-y"},
                "mode": "cbb_high_major",
            },
        ]
        existing = [
            {
                "id": "eval-1",
                "player": {"id": "p900"},
                "team_id": "team-x",
                "overall_score": 74.2,
                "mode": "cbb_d2_low_resource",
            }
        ]

        unique_payloads, duplicates, duplicate_matches = split_csv_duplicates(payloads, existing)

        self.assertEqual(len(unique_payloads), 1)
        self.assertEqual(unique_payloads[0]["player"]["id"], "p901")
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["Player ID"], "p900")
        self.assertEqual(duplicates[0]["Team"], "team-x")
        self.assertEqual(len(duplicate_matches), 1)
        self.assertEqual(duplicate_matches[0]["existing"]["id"], "eval-1")


if __name__ == "__main__":
    unittest.main()
