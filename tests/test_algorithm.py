from base64 import b64encode
from io import BytesIO
import math
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

import server
from PIL import Image, ImageDraw
from server import (
    ALGORITHM_VERSION,
    IMAGE_ANALYSIS_VERSION,
    case_timeline,
    compute_index,
    image_analysis_timeline,
    run_image_analysis,
    save_assessment,
    validate_algorithm_contract,
)


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


def image_payload(case_id, patch_size=90):
    image = Image.new("RGB", (360, 280), (191, 145, 124))
    draw = ImageDraw.Draw(image)
    left = 135 - patch_size // 2
    top = 105 - patch_size // 2
    draw.rounded_rectangle(
        [left, top, left + patch_size, top + patch_size],
        radius=18,
        fill=(142, 45, 58),
    )
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return {
        "caseId": case_id,
        "anatomicalRegion": "face",
        "imageData": "data:image/jpeg;base64," + b64encode(buffer.getvalue()).decode("ascii"),
    }


class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = server.DB_PATH
        server.DB_PATH = Path(self.temp_dir.name) / "test.sqlite3"
        server.init_db()

    def tearDown(self):
        server.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

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

    def test_saved_follow_up_assessment_reports_observed_change(self):
        first_payload = payload(3)
        first_payload.update({"clinicianName": "Dr Example", "caseId": "CASE-001"})
        second_payload = payload(6)
        second_payload.update({"clinicianName": "Dr Example", "caseId": "CASE-001"})

        first_status, first = save_assessment(first_payload)
        second_status, second = save_assessment(second_payload)

        self.assertEqual(first_status, HTTPStatus.CREATED)
        self.assertEqual(second_status, HTTPStatus.CREATED)
        self.assertEqual(first["change"]["direction"], "baseline")
        self.assertFalse(first["change"]["available"])
        self.assertEqual(second["change"]["direction"], "increased")
        self.assertGreater(second["change"]["delta"], 0)
        self.assertEqual(second["change"]["previousAssessmentId"], first["assessmentId"])
        self.assertEqual(len(second["history"]), 2)

    def test_case_timeline_returns_recent_assessments_and_latest_change(self):
        first_payload = payload(7)
        first_payload.update({"clinicianName": "Dr Example", "caseId": "CASE-002"})
        second_payload = payload(4)
        second_payload.update({"clinicianName": "Dr Example", "caseId": "CASE-002"})

        save_assessment(first_payload)
        save_assessment(second_payload)
        status, timeline = case_timeline("CASE-002")

        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(timeline["ok"])
        self.assertEqual(timeline["caseId"], "CASE-002")
        self.assertEqual(len(timeline["history"]), 2)
        self.assertEqual(timeline["latestChange"]["direction"], "decreased")
        self.assertLess(timeline["latestChange"]["delta"], 0)

    def test_image_analysis_returns_visual_measurements(self):
        status, result = run_image_analysis(image_payload("IMG-001"))

        self.assertEqual(status, HTTPStatus.CREATED)
        self.assertTrue(result["ok"])
        self.assertEqual(result["imageAnalysisVersion"], IMAGE_ANALYSIS_VERSION)
        self.assertGreaterEqual(result["visualIndex"], 0)
        self.assertIn("surface_area", result["suggestedDomains"])
        self.assertIn("qualityScore", result["quality"])
        self.assertTrue(result["overlayDataUrl"].startswith("data:image/png;base64,"))

    def test_image_analysis_timeline_omits_source_image_data(self):
        run_image_analysis(image_payload("IMG-002", patch_size=58))
        run_image_analysis(image_payload("IMG-002", patch_size=130))

        status, timeline = image_analysis_timeline("IMG-002")

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(len(timeline["history"]), 2)
        self.assertIn(timeline["latestChange"]["direction"], {"stable", "increased", "decreased"})
        self.assertNotIn("overlayDataUrl", timeline["history"][0])


if __name__ == "__main__":
    unittest.main()
