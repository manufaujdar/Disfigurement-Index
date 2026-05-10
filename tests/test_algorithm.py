import unittest

from server import ALGORITHM_VERSION, compute_index


def payload(value):
    return {
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

    def test_out_of_range_value_is_rejected(self):
        bad = payload(5)
        bad["domains"]["vascularity"] = 11
        result = compute_index(bad)
        self.assertFalse(result["ok"])
        self.assertIn("Vascularity", result["errors"][0])


if __name__ == "__main__":
    unittest.main()

