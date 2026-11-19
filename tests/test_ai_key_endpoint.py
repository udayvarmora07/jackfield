"""Environment API keys follow the provider's endpoint, not the settings API.

Security review 2026-11-19: ``POST /api/ai/settings`` could point ``base_url``
at any https or loopback host, and the next call carried ``OPENAI_API_KEY``
from the server's environment there. Keys from the environment now go only to
the provider's default endpoint, or to the one endpoint the operator names in
``SKILLS_MANAGER_AI_ENV_KEY_ENDPOINT``.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skillsmgr import ai  # noqa: E402

CUSTOM = "https://attacker.example/v1"


class EnvKeyEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _configure(self, base_url=None, api_key=None):
        payload = {"provider": "openai", "model": "gpt-test"}
        if base_url:
            payload["base_url"] = base_url
        if api_key:
            payload["api_key"] = api_key
        ai.save_settings(self.data, payload)

    def test_env_key_goes_to_the_provider_default_endpoint(self):
        self._configure()
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "sk-env-secret"}, clear=False):
            config = ai.resolve_config(self.data)
        self.assertEqual(config["key"], "sk-env-secret")

    def test_env_key_is_withheld_from_a_custom_endpoint(self):
        self._configure(base_url=CUSTOM)
        env = {"OPENAI_API_KEY": "sk-env-secret", ai.ENV_KEY_ENDPOINT_VAR: ""}
        with mock.patch.dict("os.environ", env, clear=False):
            with self.assertRaises(ai.AiError) as ctx:
                ai.resolve_config(self.data)
            settings = ai.public_settings(self.data)
        message = str(ctx.exception)
        self.assertNotIn("sk-env-secret", message)
        self.assertIn(ai.ENV_KEY_ENDPOINT_VAR, message)
        self.assertNotIn("env:", str(settings))

    def test_operator_opt_in_allows_exactly_that_endpoint(self):
        self._configure(base_url=CUSTOM)
        env = {"OPENAI_API_KEY": "sk-env-secret", ai.ENV_KEY_ENDPOINT_VAR: CUSTOM + "/"}
        with mock.patch.dict("os.environ", env, clear=False):
            self.assertEqual(ai.resolve_config(self.data)["key"], "sk-env-secret")
        self._configure(base_url="https://other.example/v1")
        with mock.patch.dict("os.environ", env, clear=False):
            with self.assertRaises(ai.AiError):
                ai.resolve_config(self.data)

    def test_a_key_stored_for_the_custom_endpoint_still_works(self):
        self._configure(base_url=CUSTOM, api_key="sk-stored-for-custom-0001")
        env = {"OPENAI_API_KEY": "sk-env-secret", ai.ENV_KEY_ENDPOINT_VAR: ""}
        with mock.patch.dict("os.environ", env, clear=False):
            self.assertEqual(ai.resolve_config(self.data)["key"], "sk-stored-for-custom-0001")


if __name__ == "__main__":
    unittest.main()
