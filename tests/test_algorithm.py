import math
import unittest

from server import ALGORITHM_VERSION, compute_index, validate_algorithm_contract


def payload(value):
    return {
        "clinicalSetting": "follow-up",
        "anatomicalRegion": "lower-limb",
        "domains": {
            "vascularity": value,
            "pigmentation": value,
            "thickness": value,
            "relief": value,
            "pliability": value,
            "surface_area": value,
            "pain": value,
            "itch": value,
            "functional_limitation": value,
            "anatomical_visibility": value,
            "clinician_global": value,
            "documentation_confidence": 8,
        }
    }


class AlgorithmTests(unittest.TestCase):
    def test_low_domain_values_produce_zero_score(self):
        result = compute_index(payload(1))
        self.assertTrue(result["ok"])
        self.assertEqual(result["algorithmVersion"], ALGORITHM_VERSION)
        self.assertEqual(result["score"], 0.0)

    def test_high_domain_values_produce_max_score(self):
        result = compute_index(payload(10))
        self.assertTrue(result["ok"])
        self.assertEqual(result["score"], 100.0)

    def test_midpoint_score_is_stable(self):
        result = compute_index(payload(5.5))
        self.assertTrue(result["ok"])
        self.assertEqual(result["score"], 50.0)
        self.assertIn("research-informed", result["severityBand"])

    def test_follow_up_setting_is_accepted(self):
        result = compute_index(payload(5))
        self.assertTrue(result["ok"])
        self.assertEqual(result["context"]["clinicalSetting"]["value"], "follow-up")

    def test_face_context_adjusts_score_upward(self):
        lower_limb = payload(5)
        face = payload(5)
        face["anatomicalRegion"] = "face"

        lower_limb_result = compute_index(lower_limb)
        face_result = compute_index(face)

        self.assertTrue(face_result["score"] > lower_limb_result["score"])
        self.assertEqual(face_result["context"]["visibilityModifierApplied"], 1.08)

    def test_out_of_range_value_is_rejected(self):
        bad = payload(5)
        bad["domains"]["vascularity"] = 11
        result = compute_index(bad)
        self.assertFalse(result["ok"])
        self.assertIn("Vascularity", result["errors"][0])

    def test_non_object_domains_are_rejected(self):
        bad = payload(5)
        bad["domains"] = []
        result = compute_index(bad)
        self.assertFalse(result["ok"])
        self.assertIn("Domains must be supplied as an object.", result["errors"])

    def test_non_finite_values_are_rejected(self):
        bad = payload(5)
        bad["domains"]["vascularity"] = math.nan
        result = compute_index(bad)
        self.assertFalse(result["ok"])
        self.assertIn("finite number", result["errors"][0])

    def test_algorithm_contract_is_valid(self):
        contract = validate_algorithm_contract()
        self.assertTrue(contract["ok"], contract["errors"])
        self.assertEqual(contract["algorithmVersion"], ALGORITHM_VERSION)
        self.assertEqual(contract["weightTotal"], 1.0)


if __name__ == "__main__":
    unittest.main()
