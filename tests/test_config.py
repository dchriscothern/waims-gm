import importlib
import os
import unittest
from unittest.mock import patch


def load_config_module():
    import app.config as config

    return importlib.reload(config)


class ConfigTests(unittest.TestCase):
    def test_sandbox_local_config_passes_without_errors(self):
        with patch.dict(
            os.environ,
            {
                "WAIMS_ENV": "sandbox",
                "WAIMS_ENV_LABEL": "Sandbox",
                "API_BASE_URL": "http://127.0.0.1:8000",
                "SUPABASE_URL": "https://sandbox-project.supabase.co",
                "SUPABASE_ANON_KEY": "sandbox-key",
            },
            clear=False,
        ):
            config = load_config_module()
            result = config.validate_runtime_settings()

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_live_env_rejects_localhost_api(self):
        with patch.dict(
            os.environ,
            {
                "WAIMS_ENV": "live",
                "WAIMS_ENV_LABEL": "Live",
                "API_BASE_URL": "http://127.0.0.1:8000",
                "SUPABASE_URL": "https://live-project.supabase.co",
                "SUPABASE_ANON_KEY": "live-key",
            },
            clear=False,
        ):
            config = load_config_module()
            result = config.validate_runtime_settings()

        self.assertIn("Live environment cannot point API_BASE_URL at localhost.", result["errors"])

    def test_sandbox_warns_if_label_says_live(self):
        with patch.dict(
            os.environ,
            {
                "WAIMS_ENV": "sandbox",
                "WAIMS_ENV_LABEL": "Live",
                "API_BASE_URL": "http://127.0.0.1:8000",
                "SUPABASE_URL": "https://sandbox-project.supabase.co",
                "SUPABASE_ANON_KEY": "sandbox-key",
            },
            clear=False,
        ):
            config = load_config_module()
            result = config.validate_runtime_settings()

        self.assertIn("WAIMS_ENV is sandbox but WAIMS_ENV_LABEL still says live.", result["warnings"])

    def test_placeholder_supabase_values_fail_validation(self):
        with patch.dict(
            os.environ,
            {
                "WAIMS_ENV": "sandbox",
                "WAIMS_ENV_LABEL": "Sandbox",
                "API_BASE_URL": "http://127.0.0.1:8000",
                "SUPABASE_URL": "https://your-sandbox-project.supabase.co",
                "SUPABASE_ANON_KEY": "your-sandbox-anon-key",
            },
            clear=False,
        ):
            config = load_config_module()
            result = config.validate_runtime_settings()

        self.assertIn("SUPABASE_URL is still set to an example placeholder value.", result["errors"])
        self.assertIn("SUPABASE_ANON_KEY is still set to an example placeholder value.", result["errors"])


if __name__ == "__main__":
    unittest.main()
