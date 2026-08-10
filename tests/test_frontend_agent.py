import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "frontend_agent"))

from frontend_agent import audit_frontend, compare_agents, improvement_prompt  # noqa: E402


class FrontendAgentTests(unittest.TestCase):
    def test_local_audit_is_deterministic_and_site_specific(self):
        report = audit_frontend(ROOT)
        self.assertEqual(report["mode"], "local_deterministic_audit")
        self.assertIn("index.html", report["filesReviewed"])
        self.assertIn("image-analysis.html", report["filesReviewed"])
        self.assertFalse(report["externalModelCalls"])
        self.assertIn("completed Disfigurement Index protocol", " ".join(report["pendingForClinicalUse"]))

    def test_current_frontend_has_no_high_audit_findings(self):
        report = audit_frontend(ROOT)
        high_findings = [finding for finding in report["findings"] if finding["severity"] == "high"]
        self.assertEqual(high_findings, [])

    def test_agent_matrix_has_release_gates(self):
        comparison = compare_agents()
        self.assertIn("Codex", {agent["name"] for agent in comparison["agents"]})
        self.assertEqual(sum(item["weight"] for item in comparison["evaluationRubric"]), 100)
        self.assertIn("algorithm contract is valid", comparison["releaseGates"])

    def test_prompt_contains_safety_constraints(self):
        prompt = improvement_prompt(audit_frontend(ROOT), compare_agents())
        self.assertIn("Do not claim diagnosis", prompt)
        self.assertIn("AI image analysis as a future capability", prompt)
        self.assertIn("proposed patch plan", prompt)
        json.dumps(prompt)


if __name__ == "__main__":
    unittest.main()
