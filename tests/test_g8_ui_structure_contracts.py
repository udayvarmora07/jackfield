"""Cross-cutting evidence and security contracts for the active interface.

Classic-only density and layout expectations were retired with that interface;
active library observations and accessibility are exercised in the v2 contracts.
"""
from pathlib import Path
import unittest

WEBUI = Path(__file__).resolve().parents[1] / "skillsmgr" / "webui"


class EvidenceContractTests(unittest.TestCase):
    def test_no_combined_score_or_inferred_state_was_introduced(self):
        for name in ("index.html", "app.js", "model.js"):
            text = (WEBUI / name).read_text(encoding="utf-8")
            for invented in ("qualityScore", "trustVerdict", "effectiveState ="):
                self.assertNotIn(invented, text, name)

    def test_application_does_not_bypass_transport_seam(self):
        app = (WEBUI / "app.js").read_text(encoding="utf-8")
        domain = (WEBUI / "domain.js").read_text(encoding="utf-8")
        self.assertIn("async function api(", domain)
        self.assertNotIn("window.fetch(", app)
        self.assertNotIn("fetch(url", app)


if __name__ == "__main__":
    unittest.main()
