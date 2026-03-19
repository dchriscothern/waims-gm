import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app, get_current_gm


class FakeResponse:
    def __init__(self, status_code, payload, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else ("" if payload is None else str(payload))

    def json(self):
        return self._payload


class QueueClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def _next_response(self, method, url, headers=None, json=None):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "json": json,
            }
        )
        if not self._responses:
            raise AssertionError(f"No queued response available for {method} {url}")
        return self._responses.pop(0)

    def get(self, url, headers=None):
        return self._next_response("GET", url, headers=headers)

    def post(self, url, headers=None, json=None):
        return self._next_response("POST", url, headers=headers, json=json)

    def delete(self, url, headers=None):
        return self._next_response("DELETE", url, headers=headers)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        app.dependency_overrides[get_current_gm] = lambda: {
            "gm_id": "gm-test",
            "token": "token-test",
        }

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ok"], True)
        self.assertEqual(data["environment"], "sandbox")
        self.assertEqual(data["environment_label"], "Sandbox")
        self.assertEqual(data["live"], False)

    def test_evaluate_returns_live_scorecard_shape(self):
        payload = {
            "player": {
                "id": "p-api-1",
                "name": "Eval Prospect",
                "position": "F",
                "age": 22,
                "offense_rating": 74.0,
                "defense_rating": 77.0,
                "shooting_rating": 72.0,
                "playmaking_rating": 61.0,
                "rebounding_rating": 70.0,
                "health_risk": 0.16,
                "upside": 0.76,
                "minutes_stability": 0.73,
                "expected_cost_tier": 2,
            },
            "ctx": {
                "team_id": "team-api",
                "timeline": "balanced",
                "needs_by_position": {"G": 0.35, "F": 0.82, "C": 0.28},
                "cap_flexibility": 0.58,
                "risk_tolerance": 0.41,
            },
            "mode": "cbb_d2_low_resource",
        }

        response = self.client.post("/evaluate", json=payload)
        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(data["components"]), {"fit", "impact", "upside", "availability", "value"})
        self.assertEqual(data["player"]["name"], payload["player"]["name"])
        self.assertIn(data["recommended_action"], {"draft", "sign", "pass"})

    def test_evaluate_mode_changes_overall_score_for_same_player(self):
        base_payload = {
            "player": {
                "id": "p-api-2",
                "name": "High Upside Guard",
                "position": "G",
                "age": 18,
                "offense_rating": 68.0,
                "defense_rating": 59.0,
                "shooting_rating": 70.0,
                "playmaking_rating": 73.0,
                "rebounding_rating": 34.0,
                "health_risk": 0.18,
                "upside": 0.94,
                "minutes_stability": 0.4,
                "expected_cost_tier": 2,
            },
            "ctx": {
                "team_id": "team-api",
                "timeline": "rebuild",
                "needs_by_position": {"G": 0.78, "F": 0.3, "C": 0.18},
                "cap_flexibility": 0.52,
                "risk_tolerance": 0.48,
            },
        }

        pro_response = self.client.post("/evaluate", json=base_payload | {"mode": "pro_wnba"})
        recruiting_response = self.client.post("/evaluate", json=base_payload | {"mode": "recruiting_only"})

        self.assertEqual(pro_response.status_code, 200)
        self.assertEqual(recruiting_response.status_code, 200)
        self.assertGreater(
            recruiting_response.json()["overall_score"],
            pro_response.json()["overall_score"],
        )

    def test_evaluate_and_save_persists_profile_and_evaluation(self):
        queued_client = QueueClient(
            [
                FakeResponse(201, None, ""),
                FakeResponse(201, [{"id": "eval-123"}]),
            ]
        )

        payload = {
            "player": {
                "id": "p-save-1",
                "name": "Save Prospect",
                "position": "F",
                "age": 22,
                "offense_rating": 75.0,
                "defense_rating": 74.0,
                "shooting_rating": 71.0,
                "playmaking_rating": 63.0,
                "rebounding_rating": 69.0,
                "health_risk": 0.14,
                "upside": 0.77,
                "minutes_stability": 0.72,
                "expected_cost_tier": 2,
            },
            "ctx": {
                "team_id": "team-save",
                "timeline": "balanced",
                "needs_by_position": {"G": 0.3, "F": 0.85, "C": 0.25},
                "cap_flexibility": 0.57,
                "risk_tolerance": 0.44,
            },
            "display_name": "Chris",
            "summary_note": "Useful rotation forward.",
            "strengths": "Versatility\nRebounding",
            "concerns": "Creation ceiling",
            "mode": "cbb_d2_low_resource",
        }

        with patch("app.main.httpx.Client", side_effect=lambda timeout=15: queued_client):
            response = self.client.post("/evaluate-and-save", json=payload)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["evaluation_id"], "eval-123")
        self.assertEqual(data["mode"], "cbb_d2_low_resource")
        self.assertEqual(len(queued_client.requests), 2)
        self.assertEqual(queued_client.requests[0]["json"], {"gm_id": "gm-test", "display_name": "Chris"})
        self.assertEqual(queued_client.requests[1]["json"]["ctx"]["mode"], "cbb_d2_low_resource")

    def test_list_evaluations_returns_saved_rows(self):
        queued_client = QueueClient(
            [
                FakeResponse(
                    200,
                    [
                        {
                            "id": "eval-1",
                            "gm_id": "gm-test",
                            "team_id": "team-1",
                            "overall_score": 66.4,
                            "recommended_action": "sign",
                            "created_at": "2026-03-18T18:30:00Z",
                            "player": {"name": "Listed Player"},
                            "summary_note": "Board-ready.",
                            "mode": "pro_wnba",
                        }
                    ],
                )
            ]
        )

        with patch("app.main.httpx.Client", side_effect=lambda timeout=15: queued_client):
            response = self.client.get("/evaluations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], "eval-1")
        self.assertEqual(response.json()[0]["mode"], "pro_wnba")

    def test_get_evaluation_detail_returns_full_record(self):
        queued_client = QueueClient(
            [
                FakeResponse(
                    200,
                    [
                        {
                            "id": "eval-detail-1",
                            "gm_id": "gm-test",
                            "team_id": "team-1",
                            "overall_score": 71.2,
                            "components": {"fit": 81.0, "impact": 69.5, "upside": 74.0, "availability": 76.0, "value": 70.0},
                            "assumptions": {"minutes_assumption": "Stable role"},
                            "tension_points": ["Price sensitivity"],
                            "recommended_action": "draft",
                            "player": {"name": "Detail Player"},
                            "ctx": {"team_id": "team-1", "mode": "cbb_high_major"},
                            "created_at": "2026-03-18T19:00:00Z",
                            "summary_note": "Priority portal target.",
                            "strengths": "Shot-making",
                            "concerns": "Cost",
                            "mode": "cbb_high_major",
                        }
                    ],
                )
            ]
        )

        with patch("app.main.httpx.Client", side_effect=lambda timeout=15: queued_client):
            response = self.client.get("/evaluations/eval-detail-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "eval-detail-1")
        self.assertEqual(response.json()["components"]["availability"], 76.0)

    def test_delete_evaluation_checks_ownership_then_deletes(self):
        queued_client = QueueClient(
            [
                FakeResponse(200, [{"id": "eval-delete-1"}]),
                FakeResponse(200, [{"id": "eval-delete-1"}]),
            ]
        )

        with patch("app.main.httpx.Client", side_effect=lambda timeout=15: queued_client):
            response = self.client.delete("/evaluations/eval-delete-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True, "deleted_id": "eval-delete-1"})
        self.assertEqual([req["method"] for req in queued_client.requests], ["GET", "DELETE"])


if __name__ == "__main__":
    unittest.main()

