#!/usr/bin/env python3
"""Local backend for the Disfigurement Index prototype.

The calculation engine is research-informed but not clinically validated as the
final Disfigurement Index. Replace ALGORITHM_DOMAINS, weights, bands, and test
vectors when the completed research protocol is supplied.
"""

from __future__ import annotations

import json
import math
import mimetypes
import sqlite3
import sys
import uuid
from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from contextlib import contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, unquote, urlparse

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
except ImportError:
    np = None
    Image = None
    ImageDraw = None
    ImageFilter = None
    ImageOps = None

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "disfigurement_index.sqlite3"
ALGORITHM_VERSION = "research-informed-composite-v1.1"
IMAGE_ANALYSIS_VERSION = "local-vision-ml-v1.0"
CHANGE_THRESHOLD = 2.0
MAX_IMAGE_BYTES = 8 * 1024 * 1024

REFERENCES = [
    {
        "id": "posas-official",
        "title": "Patient and Observer Scar Assessment Scale (POSAS)",
        "url": "https://www.posas.nl/",
        "summary": "POSAS is a validated scar-quality instrument that includes clinician and patient perspectives and is used in clinical and research settings.",
        "domains": ["vascularity", "pigmentation", "thickness", "relief", "pliability", "surface_area", "pain", "itch"],
    },
    {
        "id": "posas-rasch-2011",
        "title": "Rasch analysis of POSAS in burn scars",
        "url": "https://link.springer.com/article/10.1007/s11136-011-9924-5",
        "summary": "Rasch analysis supported POSAS reliability and validity for measuring scar quality in burn scars.",
        "domains": ["vascularity", "pigmentation", "thickness", "relief", "pliability", "surface_area"],
    },
    {
        "id": "scar-tools-review-2021",
        "title": "Scar Assessment Tools: How Do They Compare?",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8260845/",
        "summary": "Scar trials commonly assess color, thickness, relief, pliability, and surface area.",
        "domains": ["vascularity", "pigmentation", "thickness", "relief", "pliability", "surface_area"],
    },
    {
        "id": "vss-tbsa-2013",
        "title": "Modified Vancouver Scar Scale linked with total body surface area",
        "url": "https://pubmed.ncbi.nlm.nih.gov/23433706/",
        "summary": "A burn-scar method linked modified Vancouver Scar Scale domains with surface-area categories and reported inter-rater reliability.",
        "domains": ["vascularity", "pigmentation", "thickness", "pliability", "surface_area"],
    },
    {
        "id": "das59-appearance",
        "title": "Derriford Appearance Scale (DAS59)",
        "url": "https://www.derriford.info/Downloadableresources/DAS59%20DLH%20ATC.pdf",
        "summary": "DAS59 was developed to evaluate psychological distress and dysfunction associated with disfigurements and appearance concerns.",
        "domains": ["anatomical_visibility", "functional_limitation", "clinician_global"],
    },
]

ALGORITHM_DOMAINS = [
    {
        "id": "vascularity",
        "label": "Vascularity / redness",
        "category": "Observer scar quality",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.09,
        "hint": "1 = normal appearance, 10 = worst abnormal vascularity.",
        "evidence": ["posas-official", "posas-rasch-2011", "scar-tools-review-2021", "vss-tbsa-2013"],
    },
    {
        "id": "pigmentation",
        "label": "Pigmentation difference",
        "category": "Observer scar quality",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.09,
        "hint": "1 = normal surrounding skin match, 10 = worst color mismatch.",
        "evidence": ["posas-official", "posas-rasch-2011", "scar-tools-review-2021", "vss-tbsa-2013"],
    },
    {
        "id": "thickness",
        "label": "Thickness / height",
        "category": "Observer scar quality",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.10,
        "hint": "1 = normal thickness, 10 = worst raised or depressed contour.",
        "evidence": ["posas-official", "posas-rasch-2011", "scar-tools-review-2021", "vss-tbsa-2013"],
    },
    {
        "id": "relief",
        "label": "Relief / surface irregularity",
        "category": "Observer scar quality",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.10,
        "hint": "1 = regular surface, 10 = worst irregularity.",
        "evidence": ["posas-official", "posas-rasch-2011", "scar-tools-review-2021"],
    },
    {
        "id": "pliability",
        "label": "Pliability / tissue stiffness",
        "category": "Observer scar quality",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.10,
        "hint": "1 = normal pliability, 10 = worst stiffness or contracture.",
        "evidence": ["posas-official", "posas-rasch-2011", "scar-tools-review-2021", "vss-tbsa-2013"],
    },
    {
        "id": "surface_area",
        "label": "Surface area / extent",
        "category": "Extent",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.10,
        "hint": "1 = very limited involvement, 10 = very extensive involvement.",
        "evidence": ["posas-official", "posas-rasch-2011", "scar-tools-review-2021", "vss-tbsa-2013"],
    },
    {
        "id": "pain",
        "label": "Pain or tenderness",
        "category": "Symptoms",
        "min": 1,
        "max": 10,
        "default": 2,
        "weight": 0.08,
        "hint": "1 = no pain, 10 = worst pain burden.",
        "evidence": ["posas-official"],
    },
    {
        "id": "itch",
        "label": "Itch / dysesthesia",
        "category": "Symptoms",
        "min": 1,
        "max": 10,
        "default": 2,
        "weight": 0.06,
        "hint": "1 = no itch or dysesthesia, 10 = worst sensory burden.",
        "evidence": ["posas-official"],
    },
    {
        "id": "functional_limitation",
        "label": "Functional limitation",
        "category": "Clinical impact",
        "min": 1,
        "max": 10,
        "default": 2,
        "weight": 0.11,
        "hint": "1 = no functional limitation, 10 = severe limitation.",
        "evidence": ["das59-appearance"],
    },
    {
        "id": "anatomical_visibility",
        "label": "Anatomical visibility / social noticeability",
        "category": "Clinical context",
        "min": 1,
        "max": 10,
        "default": 4,
        "weight": 0.10,
        "hint": "1 = typically covered or low noticeability, 10 = highly visible region.",
        "evidence": ["das59-appearance"],
    },
    {
        "id": "clinician_global",
        "label": "Clinician global severity",
        "category": "Clinical synthesis",
        "min": 1,
        "max": 10,
        "default": 3,
        "weight": 0.07,
        "hint": "1 = normal/no disfigurement, 10 = worst overall appearance impact.",
        "evidence": ["posas-official", "das59-appearance"],
    },
]

QUALITY_DOMAINS = [
    {
        "id": "documentation_confidence",
        "label": "Documentation confidence",
        "min": 1,
        "max": 10,
        "default": 7,
        "hint": "1 = very uncertain inputs, 10 = high-confidence direct clinical assessment.",
    }
]

SEVERITY_BANDS = [
    {"min": 0, "max": 19.9, "label": "Minimal research-informed band"},
    {"min": 20, "max": 39.9, "label": "Mild research-informed band"},
    {"min": 40, "max": 59.9, "label": "Moderate research-informed band"},
    {"min": 60, "max": 79.9, "label": "Severe research-informed band"},
    {"min": 80, "max": 100, "label": "Very severe research-informed band"},
]

ANATOMICAL_CONTEXT = {
    "face": {"label": "Face", "visibilityModifier": 1.08, "note": "High social noticeability region."},
    "neck": {"label": "Neck", "visibilityModifier": 1.04, "note": "Usually visible region with movement relevance."},
    "upper-limb": {"label": "Upper limb", "visibilityModifier": 1.02, "note": "Visibility varies with clothing and occupation."},
    "lower-limb": {"label": "Lower limb", "visibilityModifier": 1.00, "note": "Visibility varies with clothing and mobility burden."},
    "trunk": {"label": "Trunk", "visibilityModifier": 0.96, "note": "Often covered, but may have major functional or psychosocial impact."},
    "multiple": {"label": "Multiple regions", "visibilityModifier": 1.06, "note": "Multiple-region involvement increases documentation complexity."},
}

CLINICAL_SETTING_CONTEXT = {
    "outpatient": "Routine outpatient assessment.",
    "inpatient": "Inpatient assessment; document acute illness, dressings, and wound-stage limitations.",
    "surgical": "Surgical assessment; compare pre- and post-intervention scores only when measurement conditions match.",
    "medico-legal": "Medico-legal documentation; preserve source photographs, scorer identity, and formula version.",
    "follow-up": "Follow-up review; compare with previous cases only when scoring conditions match.",
}

DOMAIN_GROUPS = [
    {
        "id": "scar_quality",
        "label": "Scar and surface quality",
        "domains": ["vascularity", "pigmentation", "thickness", "relief", "pliability"],
    },
    {
        "id": "extent_visibility",
        "label": "Extent and visibility",
        "domains": ["surface_area", "anatomical_visibility"],
    },
    {
        "id": "symptoms_function",
        "label": "Symptoms and function",
        "domains": ["pain", "itch", "functional_limitation"],
    },
    {
        "id": "clinical_synthesis",
        "label": "Clinician synthesis",
        "domains": ["clinician_global"],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                clinician_name TEXT NOT NULL,
                case_id TEXT NOT NULL,
                clinical_setting TEXT NOT NULL,
                anatomical_region TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                score REAL NOT NULL,
                severity_band TEXT NOT NULL,
                completeness REAL NOT NULL,
                confidence REAL NOT NULL,
                inputs_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS forum_comments (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                topic TEXT NOT NULL,
                comment TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS image_analyses (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                case_id TEXT NOT NULL,
                anatomical_region TEXT NOT NULL,
                quality_score REAL NOT NULL,
                visual_index REAL NOT NULL,
                detected_area_percent REAL NOT NULL,
                result_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            );
            """
        )


def normalize(value: float, minimum: float, maximum: float) -> float:
    if maximum <= minimum:
        return 0.0
    return (value - minimum) / (maximum - minimum)


def band_for_score(score: float) -> str:
    for band in SEVERITY_BANDS:
        if band["min"] <= score <= band["max"]:
            return band["label"]
    return SEVERITY_BANDS[-1]["label"]


def validate_domain_value(domain: dict[str, Any], value: Any) -> tuple[float | None, str | None]:
    if value is None or value == "":
        return None, f"{domain['label']} is required."
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None, f"{domain['label']} must be numeric."
    if not math.isfinite(numeric):
        return None, f"{domain['label']} must be a finite number."
    if numeric < domain["min"] or numeric > domain["max"]:
        return None, f"{domain['label']} must be between {domain['min']} and {domain['max']}."
    return numeric, None


def validate_algorithm_contract() -> dict[str, Any]:
    errors: list[str] = []
    domain_ids = [domain["id"] for domain in ALGORITHM_DOMAINS]
    quality_ids = [domain["id"] for domain in QUALITY_DOMAINS]
    all_ids = domain_ids + quality_ids

    if len(set(domain_ids)) != len(domain_ids):
        errors.append("Algorithm domain ids must be unique.")
    if len(set(all_ids)) != len(all_ids):
        errors.append("Quality domain ids must not duplicate scoring domain ids.")

    weight_total = sum(float(domain["weight"]) for domain in ALGORITHM_DOMAINS)
    if not math.isclose(weight_total, 1.0, abs_tol=0.0001):
        errors.append("Algorithm domain weights must sum to 1.0.")

    known = set(domain_ids)
    for group in DOMAIN_GROUPS:
        unknown = [domain_id for domain_id in group["domains"] if domain_id not in known]
        if unknown:
            errors.append(f"Domain group {group['id']} references unknown domains: {', '.join(unknown)}.")

    return {
        "ok": not errors,
        "errors": errors,
        "algorithmVersion": ALGORITHM_VERSION,
        "domainCount": len(ALGORITHM_DOMAINS),
        "qualityDomainCount": len(QUALITY_DOMAINS),
        "weightTotal": round(weight_total, 4),
    }


def compute_index(payload: dict[str, Any]) -> dict[str, Any]:
    domains = payload.get("domains")
    if domains is None:
        domains = {}
    anatomical_region = str(payload.get("anatomicalRegion") or "").strip()
    clinical_setting = str(payload.get("clinicalSetting") or "").strip()
    values: dict[str, float] = {}
    errors: list[str] = []

    if not isinstance(domains, dict):
        return {
            "ok": False,
            "errors": ["Domains must be supplied as an object."],
            "algorithmVersion": ALGORITHM_VERSION,
        }

    if anatomical_region and anatomical_region not in ANATOMICAL_CONTEXT:
        errors.append("Anatomical region is not recognized.")
    if clinical_setting and clinical_setting not in CLINICAL_SETTING_CONTEXT:
        errors.append("Clinical setting is not recognized.")

    for domain in ALGORITHM_DOMAINS:
        value, error = validate_domain_value(domain, domains.get(domain["id"]))
        if error:
            errors.append(error)
        else:
            values[domain["id"]] = value if value is not None else domain["default"]

    quality_values: dict[str, float] = {}
    for domain in QUALITY_DOMAINS:
        value, error = validate_domain_value(domain, domains.get(domain["id"]))
        if error:
            errors.append(error)
        else:
            quality_values[domain["id"]] = value if value is not None else domain["default"]

    if errors:
        return {
            "ok": False,
            "errors": errors,
            "algorithmVersion": ALGORITHM_VERSION,
        }

    weighted_parts = []
    weighted_total = 0.0
    for domain in ALGORITHM_DOMAINS:
        value = values[domain["id"]]
        normalized = normalize(value, domain["min"], domain["max"])
        contribution = normalized * domain["weight"]
        weighted_total += contribution
        weighted_parts.append(
            {
                "id": domain["id"],
                "label": domain["label"],
                "category": domain["category"],
                "raw": value,
                "normalized": round(normalized, 4),
                "weight": domain["weight"],
                "contribution": round(contribution * 100, 2),
                "evidence": domain["evidence"],
            }
        )

    base_score = round(max(0.0, min(weighted_total * 100, 100.0)), 1)
    region_context = ANATOMICAL_CONTEXT.get(anatomical_region, {"visibilityModifier": 1.0, "label": "Not supplied", "note": "No anatomical context supplied."})
    context_adjusted_score = round(max(0.0, min(base_score * region_context["visibilityModifier"], 100.0)), 1)
    documentation_confidence = quality_values["documentation_confidence"]
    confidence = round(normalize(documentation_confidence, 1, 10) * 100, 1)
    drivers = sorted(weighted_parts, key=lambda item: item["contribution"], reverse=True)
    grouped_scores = compute_group_scores(weighted_parts)

    warnings = [
        "This is a research-informed development algorithm, not the final validated Disfigurement Index formula.",
        "Use only for prototype review until the completed research protocol and reference test cases are integrated.",
    ]
    if confidence < 45:
        warnings.append("Documentation confidence is low; repeat assessment or add reviewer confirmation before interpretation.")
    if float(domains.get("clinician_global", 1)) >= 8 and context_adjusted_score < 60:
        warnings.append("Clinician global severity is high relative to the composite score; review domain inputs for consistency.")
    if values["functional_limitation"] >= 7 and values["pain"] <= 3 and values["itch"] <= 3:
        warnings.append("Functional limitation is high while symptom scores are low; document contracture, movement restriction, or non-pain functional mechanisms.")
    if anatomical_region == "multiple" and values["surface_area"] < 4:
        warnings.append("Multiple anatomical regions selected with low extent score; confirm surface-area grading.")

    recommendations = clinical_recommendations(context_adjusted_score, confidence, values, clinical_setting)

    result = {
        "ok": True,
        "algorithmVersion": ALGORITHM_VERSION,
        "score": context_adjusted_score,
        "baseScore": base_score,
        "contextAdjustedScore": context_adjusted_score,
        "severityBand": band_for_score(context_adjusted_score),
        "completeness": 100.0,
        "confidence": confidence,
        "highestDriver": drivers[0]["label"],
        "drivers": drivers[:5],
        "groupedScores": grouped_scores,
        "allContributions": weighted_parts,
        "context": {
            "anatomicalRegion": region_context,
            "clinicalSetting": {
                "value": clinical_setting or "not-supplied",
                "note": CLINICAL_SETTING_CONTEXT.get(clinical_setting, "No clinical setting supplied."),
            },
            "visibilityModifierApplied": region_context["visibilityModifier"],
        },
        "recommendations": recommendations,
        "warnings": warnings,
        "references": REFERENCES,
        "calculatedAt": now_iso(),
    }
    return result


def compute_group_scores(weighted_parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {part["id"]: part for part in weighted_parts}
    groups: list[dict[str, Any]] = []
    for group in DOMAIN_GROUPS:
        selected = [by_id[domain_id] for domain_id in group["domains"] if domain_id in by_id]
        weight_total = sum(item["weight"] for item in selected)
        contribution_total = sum(item["contribution"] for item in selected)
        score = round((contribution_total / (weight_total * 100)) * 100, 1) if weight_total else 0.0
        groups.append(
            {
                "id": group["id"],
                "label": group["label"],
                "score": score,
                "contribution": round(contribution_total, 2),
                "domains": [item["label"] for item in selected],
            }
        )
    return groups


def clinical_recommendations(score: float, confidence: float, values: dict[str, float], clinical_setting: str) -> list[str]:
    recommendations = [
        "Record scorer identity, assessment date, formula version, and source documentation used for scoring.",
        "Use the same scoring conditions for longitudinal comparison whenever possible.",
    ]
    if score >= 60:
        recommendations.append("Consider specialist review or second scoring before final interpretation.")
    if confidence < 70:
        recommendations.append("Improve documentation quality before using the result for reports or comparison.")
    if values["functional_limitation"] >= 7:
        recommendations.append("Document functional limitation separately from cosmetic appearance and consider functional outcome measures.")
    if clinical_setting == "medico-legal":
        recommendations.append("For medico-legal use, attach source evidence and preserve an immutable calculation record.")
    return recommendations


def image_stack_available() -> bool:
    return np is not None and Image is not None and ImageDraw is not None and ImageFilter is not None and ImageOps is not None


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(float(value), maximum))


def scaled_domain_score(value: float, lower: float, upper: float) -> float:
    if upper <= lower:
        return 1.0
    return round(1.0 + 9.0 * clamp((value - lower) / (upper - lower)), 1)


def decode_image_data(image_data: str) -> tuple[Any | None, str | None]:
    if not image_stack_available():
        return None, "Image analysis dependencies are not installed."
    if not image_data:
        return None, "Image data is required."
    raw_data = image_data.split(",", 1)[1] if "," in image_data and image_data.startswith("data:") else image_data
    try:
        binary = b64decode(raw_data, validate=True)
    except (Base64Error, ValueError):
        return None, "Image data is not valid base64."
    if not binary:
        return None, "Image data is empty."
    if len(binary) > MAX_IMAGE_BYTES:
        return None, "Image is too large. Use a photo under 8 MB."
    try:
        image = ImageOps.exif_transpose(Image.open(BytesIO(binary))).convert("RGB")
    except Exception:
        return None, "Image could not be opened."
    width, height = image.size
    if width < 120 or height < 120:
        return None, "Image resolution is too small for analysis."
    return image, None


def resized_image(image: Any, max_side: int = 720) -> Any:
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    if scale >= 1.0:
        return image.copy()
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def normalized_array(values: Any) -> Any:
    spread = float(np.percentile(values, 95) - np.percentile(values, 5))
    if spread <= 1e-9:
        return np.zeros_like(values, dtype=float)
    return np.clip((values - np.percentile(values, 5)) / spread, 0.0, 1.0)


def local_kmeans(features: Any, cluster_count: int = 4, iterations: int = 12) -> Any:
    total = features.shape[0]
    if total <= cluster_count:
        return np.zeros(total, dtype=int)
    score_axis = features[:, 0] * 0.25 + features[:, 1] * 0.2 + features[:, 2] * 0.2 + features[:, 3] * 0.25 + features[:, 4] * 0.1
    order = np.argsort(score_axis)
    initial_positions = np.linspace(0, total - 1, cluster_count, dtype=int)
    centers = features[order[initial_positions]].copy()
    labels = np.zeros(total, dtype=int)
    for _ in range(iterations):
        distances = ((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        next_labels = np.argmin(distances, axis=1)
        if np.array_equal(labels, next_labels):
            break
        labels = next_labels
        for cluster in range(cluster_count):
            selected = features[labels == cluster]
            if selected.size:
                centers[cluster] = selected.mean(axis=0)
    return labels


def smooth_mask(mask: Any, keep: Any, rounds: int = 2) -> Any:
    current = mask.astype(bool)
    for _ in range(rounds):
        padded = np.pad(current, 1, mode="constant")
        neighbors = (
            padded[:-2, :-2] + padded[:-2, 1:-1] + padded[:-2, 2:]
            + padded[1:-1, :-2] + padded[1:-1, 1:-1] + padded[1:-1, 2:]
            + padded[2:, :-2] + padded[2:, 1:-1] + padded[2:, 2:]
        )
        current = (neighbors >= 4) & keep
    return current


def image_quality_metrics(rgb: Any, original_size: tuple[int, int]) -> dict[str, float]:
    luma = rgb[:, :, 0] * 0.299 + rgb[:, :, 1] * 0.587 + rgb[:, :, 2] * 0.114
    grad_y, grad_x = np.gradient(luma)
    gradient = np.hypot(grad_x, grad_y)
    width, height = original_size
    brightness = float(luma.mean())
    contrast = float(luma.std())
    sharpness = float(np.percentile(gradient, 95))
    resolution_score = clamp((width * height) / (900 * 700)) * 100
    brightness_score = (1.0 - clamp(abs(brightness - 0.52) / 0.42)) * 100
    contrast_score = clamp(contrast / 0.22) * 100
    sharpness_score = clamp(sharpness / 0.055) * 100
    quality_score = round(0.28 * resolution_score + 0.26 * brightness_score + 0.22 * contrast_score + 0.24 * sharpness_score, 1)
    return {
        "qualityScore": quality_score,
        "brightness": round(brightness * 100, 1),
        "contrast": round(contrast * 100, 1),
        "sharpness": round(sharpness_score, 1),
        "resolutionScore": round(resolution_score, 1),
    }


def segment_visual_change(rgb: Any) -> tuple[Any, dict[str, float]]:
    height, width, _ = rgb.shape
    red = rgb[:, :, 0]
    green = rgb[:, :, 1]
    blue = rgb[:, :, 2]
    luma = red * 0.299 + green * 0.587 + blue * 0.114
    grad_y, grad_x = np.gradient(luma)
    gradient = normalized_array(np.hypot(grad_x, grad_y))
    median_rgb = np.median(rgb.reshape(-1, 3), axis=0)
    median_luma = float(np.median(luma))
    color_distance = np.sqrt(((rgb - median_rgb) ** 2).sum(axis=2)) / math.sqrt(3)
    red_excess = np.maximum(red - ((green + blue) / 2), 0.0)
    luma_shift = np.abs(luma - median_luma)
    anomaly = (
        0.43 * normalized_array(color_distance)
        + 0.24 * gradient
        + 0.20 * normalized_array(red_excess)
        + 0.13 * normalized_array(luma_shift)
    )
    features = np.stack(
        [
            normalized_array(color_distance).reshape(-1),
            gradient.reshape(-1),
            normalized_array(red_excess).reshape(-1),
            normalized_array(luma_shift).reshape(-1),
            luma.reshape(-1),
        ],
        axis=1,
    )
    total = features.shape[0]
    sample_limit = 36000
    if total > sample_limit:
        sample_idx = np.linspace(0, total - 1, sample_limit, dtype=int)
        sample_features = features[sample_idx]
        labels_sample = local_kmeans(sample_features)
        centers_list = []
        fallback_order = np.linspace(0, sample_features.shape[0] - 1, 4, dtype=int)
        for cluster in range(4):
            selected = sample_features[labels_sample == cluster]
            if selected.size:
                centers_list.append(selected.mean(axis=0))
            else:
                centers_list.append(sample_features[fallback_order[cluster]])
        centers = np.array(centers_list)
        labels = np.argmin(((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2), axis=1)
    else:
        labels = local_kmeans(features)
    labels_image = labels.reshape(height, width)
    cluster_scores = []
    for cluster in range(4):
        cluster_mask = labels_image == cluster
        area = float(cluster_mask.mean())
        if area <= 0:
            cluster_scores.append(-1.0)
            continue
        area_penalty = 0.35 if area > 0.72 else 1.0
        cluster_scores.append(float(anomaly[cluster_mask].mean()) * area_penalty)
    target_cluster = int(np.argmax(cluster_scores))
    target_cluster_mask = labels_image == target_cluster
    threshold = max(float(np.quantile(anomaly, 0.78)), float(anomaly[target_cluster_mask].mean()) * 0.72)
    mask = target_cluster_mask & (anomaly >= threshold)
    if float(mask.mean()) < 0.003:
        mask = anomaly >= float(np.quantile(anomaly, 0.92))
    if float(mask.mean()) > 0.45:
        mask = anomaly >= float(np.quantile(anomaly, 0.86))
    mask = smooth_mask(mask, anomaly >= float(np.quantile(anomaly, 0.60)))

    background = ~mask
    if not background.any():
        background = np.ones_like(mask, dtype=bool)
    if mask.any():
        target_rgb = rgb[mask].mean(axis=0)
        background_rgb = rgb[background].mean(axis=0)
        target_luma = float(luma[mask].mean())
        background_luma = float(luma[background].mean())
        color_contrast = float(np.linalg.norm(target_rgb - background_rgb) / math.sqrt(3))
        redness = float(np.maximum(red_excess[mask].mean(), 0.0))
        pigment_shift = abs(target_luma - background_luma)
        texture = float(gradient[mask].mean())
    else:
        color_contrast = redness = pigment_shift = texture = 0.0
    metrics = {
        "detectedAreaPercent": round(float(mask.mean()) * 100, 1),
        "colorContrast": round(color_contrast * 100, 1),
        "rednessSignal": round(redness * 100, 1),
        "pigmentShift": round(pigment_shift * 100, 1),
        "textureIrregularity": round(texture * 100, 1),
    }
    return mask, metrics


def overlay_data_url(image: Any, mask: Any) -> str:
    base = image.convert("RGBA")
    mask_image = Image.fromarray(mask.astype("uint8") * 255).resize(base.size, Image.Resampling.NEAREST)
    fill = Image.new("RGBA", base.size, (15, 118, 110, 0))
    fill.putalpha(mask_image.point(lambda pixel: 86 if pixel else 0))
    composite = Image.alpha_composite(base, fill)
    edge = mask_image.filter(ImageFilter.FIND_EDGES)
    edge_layer = Image.new("RGBA", base.size, (176, 106, 0, 0))
    edge_layer.putalpha(edge.point(lambda pixel: 210 if pixel else 0))
    composite = Image.alpha_composite(composite, edge_layer)
    buffer = BytesIO()
    composite.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode("ascii")


def image_domain_suggestions(area_metrics: dict[str, float], quality_metrics: dict[str, float]) -> dict[str, float]:
    area = area_metrics["detectedAreaPercent"]
    color = area_metrics["colorContrast"]
    redness = area_metrics["rednessSignal"]
    pigment = area_metrics["pigmentShift"]
    texture = area_metrics["textureIrregularity"]
    surface_area = scaled_domain_score(area, 1.0, 35.0)
    pigmentation = scaled_domain_score(max(color, pigment), 6.0, 36.0)
    vascularity = scaled_domain_score(redness, 2.0, 26.0)
    relief = scaled_domain_score(texture, 8.0, 42.0)
    clinician_global = round(0.25 * surface_area + 0.26 * pigmentation + 0.21 * vascularity + 0.28 * relief, 1)
    documentation_confidence = round(1.0 + 9.0 * clamp(quality_metrics["qualityScore"] / 100.0), 1)
    return {
        "vascularity": vascularity,
        "pigmentation": pigmentation,
        "relief": relief,
        "surface_area": surface_area,
        "clinician_global": clinician_global,
        "documentation_confidence": documentation_confidence,
    }


def visual_index_payload(suggestions: dict[str, float], anatomical_region: str) -> dict[str, Any]:
    domains = {domain["id"]: domain["default"] for domain in ALGORITHM_DOMAINS}
    domains.update({domain["id"]: domain["default"] for domain in QUALITY_DOMAINS})
    domains.update(suggestions)
    return {
        "clinicalSetting": "follow-up",
        "anatomicalRegion": anatomical_region,
        "domains": domains,
    }


def image_observations(area_metrics: dict[str, float], quality_metrics: dict[str, float]) -> list[str]:
    observations = []
    if quality_metrics["qualityScore"] >= 70:
        observations.append("Image quality is suitable for structured visual review.")
    else:
        observations.append("Image quality may limit automated visual review.")
    if area_metrics["detectedAreaPercent"] >= 1:
        observations.append(f"Detected visible-change region covers about {area_metrics['detectedAreaPercent']}% of the analyzed image.")
    else:
        observations.append("No large localized visible-change region was detected.")
    if area_metrics["rednessSignal"] >= 12:
        observations.append("Color analysis found an increased redness signal in the detected region.")
    if area_metrics["pigmentShift"] >= 12:
        observations.append("Color analysis found a pigmentation difference from the surrounding image.")
    if area_metrics["textureIrregularity"] >= 20:
        observations.append("Texture analysis found surface irregularity in the detected region.")
    return observations


def run_image_analysis(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    case_id = str(payload.get("caseId", "")).strip()
    anatomical_region = str(payload.get("anatomicalRegion", "face")).strip() or "face"
    if not case_id:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": ["Case ID is required."]}
    if anatomical_region not in ANATOMICAL_CONTEXT:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": ["Anatomical region is not recognized."]}

    image, error = decode_image_data(str(payload.get("imageData", "")))
    if error:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": [error]}

    analysis_image = resized_image(image)
    rgb = np.asarray(analysis_image, dtype=np.float32) / 255.0
    quality_metrics = image_quality_metrics(rgb, image.size)
    mask, area_metrics = segment_visual_change(rgb)
    suggestions = image_domain_suggestions(area_metrics, quality_metrics)
    visual_result = compute_index(visual_index_payload(suggestions, anatomical_region))
    if not visual_result["ok"]:
        return HTTPStatus.UNPROCESSABLE_ENTITY, visual_result

    analysis_id = str(uuid.uuid4())
    created_at = now_iso()
    result = {
        "ok": True,
        "analysisId": analysis_id,
        "createdAt": created_at,
        "caseId": case_id,
        "anatomicalRegion": anatomical_region,
        "imageAnalysisVersion": IMAGE_ANALYSIS_VERSION,
        "quality": quality_metrics,
        "measurements": area_metrics,
        "suggestedDomains": suggestions,
        "visualIndex": visual_result["score"],
        "severityBand": visual_result["severityBand"],
        "confidence": visual_result["confidence"],
        "observations": image_observations(area_metrics, quality_metrics),
        "overlayDataUrl": overlay_data_url(analysis_image, mask),
        "calculatorPayload": visual_index_payload(suggestions, anatomical_region),
    }
    persistable = {key: value for key, value in result.items() if key not in {"overlayDataUrl"}}

    with db() as conn:
        previous_row = conn.execute(
            """
            SELECT id, created_at, case_id, anatomical_region, quality_score,
                   visual_index, detected_area_percent, result_json
            FROM image_analyses
            WHERE case_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (case_id,),
        ).fetchone()
        previous = summarize_image_analysis(previous_row) if previous_row else None
        change = assessment_change({"score": result["visualIndex"]}, {"score": previous["visualIndex"], "assessmentId": previous["analysisId"], "createdAt": previous["createdAt"]} if previous else None)
        conn.execute(
            """
            INSERT INTO image_analyses (
                id, created_at, case_id, anatomical_region, quality_score,
                visual_index, detected_area_percent, result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                created_at,
                case_id,
                anatomical_region,
                quality_metrics["qualityScore"],
                result["visualIndex"],
                area_metrics["detectedAreaPercent"],
                json.dumps(persistable, separators=(",", ":")),
            ),
        )
        record_audit(
            conn,
            "image_analysis.created",
            "image_analysis",
            analysis_id,
            {
                "imageAnalysisVersion": IMAGE_ANALYSIS_VERSION,
                "caseId": case_id,
                "visualIndex": result["visualIndex"],
                "qualityScore": quality_metrics["qualityScore"],
            },
        )
        history = [summarize_image_analysis(row) for row in image_analysis_rows(conn, case_id)]

    result["change"] = change
    result["history"] = history
    return HTTPStatus.CREATED, result


def summarize_image_analysis(row: dict[str, Any]) -> dict[str, Any]:
    result = parse_result_json(row.get("result_json"))
    visual_index = float(row.get("visual_index", result.get("visualIndex", 0.0)))
    quality_score = float(row.get("quality_score", result.get("quality", {}).get("qualityScore", 0.0)))
    detected_area = float(row.get("detected_area_percent", result.get("measurements", {}).get("detectedAreaPercent", 0.0)))
    return {
        "analysisId": row.get("id"),
        "createdAt": row.get("created_at"),
        "caseId": row.get("case_id"),
        "anatomicalRegion": row.get("anatomical_region"),
        "visualIndex": round(visual_index, 1),
        "qualityScore": round(quality_score, 1),
        "detectedAreaPercent": round(detected_area, 1),
        "suggestedDomains": result.get("suggestedDomains", {}),
        "imageAnalysisVersion": result.get("imageAnalysisVersion", IMAGE_ANALYSIS_VERSION),
    }


def image_analysis_rows(conn: sqlite3.Connection, case_id: str, limit: int = 12) -> list[dict[str, Any]]:
    normalized_limit = max(1, min(int(limit), 50))
    return conn.execute(
        """
        SELECT id, created_at, case_id, anatomical_region, quality_score,
               visual_index, detected_area_percent, result_json
        FROM image_analyses
        WHERE case_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT ?
        """,
        (case_id, normalized_limit),
    ).fetchall()


def image_analysis_timeline(case_id: str) -> tuple[int, dict[str, Any]]:
    normalized = str(case_id or "").strip()
    if not normalized:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": ["Case ID is required."]}
    with db() as conn:
        history = [summarize_image_analysis(row) for row in image_analysis_rows(conn, normalized)]
    previous = {"score": history[1]["visualIndex"], "assessmentId": history[1]["analysisId"], "createdAt": history[1]["createdAt"]} if len(history) > 1 else None
    latest_change = assessment_change({"score": history[0]["visualIndex"]}, previous) if history else None
    return HTTPStatus.OK, {
        "ok": True,
        "caseId": normalized,
        "history": history,
        "latestChange": latest_change,
    }


def parse_result_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def summarize_assessment(row: dict[str, Any]) -> dict[str, Any]:
    result = parse_result_json(row.get("result_json"))
    score = float(row.get("score", result.get("score", 0.0)))
    confidence = float(row.get("confidence", result.get("confidence", 0.0)))
    return {
        "assessmentId": row.get("id"),
        "createdAt": row.get("created_at"),
        "caseId": row.get("case_id"),
        "clinicalSetting": row.get("clinical_setting"),
        "anatomicalRegion": row.get("anatomical_region"),
        "score": round(score, 1),
        "severityBand": row.get("severity_band") or result.get("severityBand") or band_for_score(score),
        "confidence": round(confidence, 1),
        "highestDriver": result.get("highestDriver", "Not available"),
        "algorithmVersion": result.get("algorithmVersion", ALGORITHM_VERSION),
    }


def assessment_change(current_result: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    current_score = round(float(current_result.get("score", 0.0)), 1)
    comparison_note = "Compare only when scoring conditions and documentation quality are similar."
    if not previous:
        return {
            "available": False,
            "direction": "baseline",
            "currentScore": current_score,
            "previousScore": None,
            "delta": None,
            "absoluteDelta": None,
            "previousAssessmentId": None,
            "previousCreatedAt": None,
            "interpretation": "First saved assessment for this Case ID.",
            "comparisonNote": comparison_note,
        }

    previous_score = round(float(previous.get("score", 0.0)), 1)
    delta = round(current_score - previous_score, 1)
    absolute_delta = round(abs(delta), 1)
    if absolute_delta < CHANGE_THRESHOLD:
        direction = "stable"
        interpretation = "No material score change from the previous saved assessment."
    elif delta > 0:
        direction = "increased"
        interpretation = "Composite score increased from the previous saved assessment."
    else:
        direction = "decreased"
        interpretation = "Composite score decreased from the previous saved assessment."

    return {
        "available": True,
        "direction": direction,
        "currentScore": current_score,
        "previousScore": previous_score,
        "delta": delta,
        "absoluteDelta": absolute_delta,
        "previousAssessmentId": previous.get("assessmentId"),
        "previousCreatedAt": previous.get("createdAt"),
        "interpretation": interpretation,
        "comparisonNote": comparison_note,
    }


def case_assessment_rows(conn: sqlite3.Connection, case_id: str, limit: int = 12) -> list[dict[str, Any]]:
    normalized_limit = max(1, min(int(limit), 50))
    return conn.execute(
        """
        SELECT id, created_at, case_id, clinical_setting, anatomical_region,
               score, severity_band, confidence, result_json
        FROM assessments
        WHERE case_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT ?
        """,
        (case_id, normalized_limit),
    ).fetchall()


def list_case_assessments(case_id: str, limit: int = 12) -> list[dict[str, Any]]:
    normalized = str(case_id or "").strip()
    if not normalized:
        return []
    with db() as conn:
        return [summarize_assessment(row) for row in case_assessment_rows(conn, normalized, limit)]


def case_timeline(case_id: str) -> tuple[int, dict[str, Any]]:
    normalized = str(case_id or "").strip()
    if not normalized:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": ["Case ID is required."]}
    history = list_case_assessments(normalized)
    latest_change = assessment_change(history[0], history[1] if len(history) > 1 else None) if history else None
    return HTTPStatus.OK, {
        "ok": True,
        "caseId": normalized,
        "history": history,
        "latestChange": latest_change,
    }


def record_audit(conn: sqlite3.Connection, event_type: str, entity_type: str, entity_id: str, metadata: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO audit_events (id, created_at, event_type, entity_type, entity_id, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (str(uuid.uuid4()), now_iso(), event_type, entity_type, entity_id, json.dumps(metadata, separators=(",", ":"))),
    )


def save_assessment(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    required_text = ["clinicianName", "caseId", "clinicalSetting", "anatomicalRegion"]
    missing = [field for field in required_text if not str(payload.get(field, "")).strip()]
    if missing:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": [f"Missing required field: {field}" for field in missing]}

    result = compute_index(payload)
    if not result["ok"]:
        return HTTPStatus.UNPROCESSABLE_ENTITY, result

    assessment_id = str(uuid.uuid4())
    created_at = now_iso()
    case_id = str(payload["caseId"]).strip()
    with db() as conn:
        previous_row = conn.execute(
            """
            SELECT id, created_at, case_id, clinical_setting, anatomical_region,
                   score, severity_band, confidence, result_json
            FROM assessments
            WHERE case_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (case_id,),
        ).fetchone()
        previous = summarize_assessment(previous_row) if previous_row else None
        change = assessment_change(result, previous)
        conn.execute(
            """
            INSERT INTO assessments (
                id, created_at, clinician_name, case_id, clinical_setting, anatomical_region,
                notes, score, severity_band, completeness, confidence, inputs_json, result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assessment_id,
                created_at,
                str(payload["clinicianName"]).strip(),
                case_id,
                str(payload["clinicalSetting"]).strip(),
                str(payload["anatomicalRegion"]).strip(),
                str(payload.get("notes", "")).strip(),
                result["score"],
                result["severityBand"],
                result["completeness"],
                result["confidence"],
                json.dumps(payload, separators=(",", ":")),
                json.dumps(result, separators=(",", ":")),
            ),
        )
        record_audit(
            conn,
            "assessment.created",
            "assessment",
            assessment_id,
            {
                "algorithmVersion": ALGORITHM_VERSION,
                "score": result["score"],
                "caseId": case_id,
                "changeDirection": change["direction"],
                "scoreDelta": change["delta"],
            },
        )
        history = [summarize_assessment(row) for row in case_assessment_rows(conn, case_id)]

    result["assessmentId"] = assessment_id
    result["createdAt"] = created_at
    result["change"] = change
    result["history"] = history
    return HTTPStatus.CREATED, result


def list_forum_comments() -> list[dict[str, Any]]:
    with db() as conn:
        return conn.execute(
            """
            SELECT id, created_at, doctor_name, topic, comment
            FROM forum_comments
            ORDER BY created_at DESC
            LIMIT 100
            """
        ).fetchall()


def save_forum_comment(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    doctor_name = str(payload.get("doctorName", "")).strip()
    topic = str(payload.get("topic", "")).strip()
    comment = str(payload.get("comment", "")).strip()
    if not doctor_name or not topic or not comment:
        return HTTPStatus.BAD_REQUEST, {"ok": False, "errors": ["Doctor name, topic, and comment are required."]}

    comment_id = str(uuid.uuid4())
    created_at = now_iso()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO forum_comments (id, created_at, doctor_name, topic, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (comment_id, created_at, doctor_name, topic, comment),
        )
        record_audit(conn, "forum_comment.created", "forum_comment", comment_id, {"topic": topic})

    return HTTPStatus.CREATED, {
        "ok": True,
        "id": comment_id,
        "created_at": created_at,
        "doctor_name": doctor_name,
        "topic": topic,
        "comment": comment,
    }


class AppHandler(SimpleHTTPRequestHandler):
    server_version = "DisfigurementIndexPrototype/1.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def send_json(self, status: int, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

    def read_json(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON body.")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            contract = validate_algorithm_contract()
            status = HTTPStatus.OK if contract["ok"] else HTTPStatus.INTERNAL_SERVER_ERROR
            self.send_json(
                status,
                {
                    "ok": contract["ok"],
                    "time": now_iso(),
                    "algorithmVersion": ALGORITHM_VERSION,
                    "imageAnalysisVersion": IMAGE_ANALYSIS_VERSION,
                    "imageAnalysisAvailable": image_stack_available(),
                    "algorithmContract": contract,
                },
            )
            return
        if path == "/api/config":
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "algorithmVersion": ALGORITHM_VERSION,
                    "imageAnalysisVersion": IMAGE_ANALYSIS_VERSION,
                    "imageAnalysisAvailable": image_stack_available(),
                    "domains": ALGORITHM_DOMAINS,
                    "qualityDomains": QUALITY_DOMAINS,
                    "bands": SEVERITY_BANDS,
                    "domainGroups": DOMAIN_GROUPS,
                    "anatomicalContext": ANATOMICAL_CONTEXT,
                    "clinicalSettingContext": CLINICAL_SETTING_CONTEXT,
                    "algorithmContract": validate_algorithm_contract(),
                    "references": REFERENCES,
                },
            )
            return
        if path == "/api/forum":
            self.send_json(HTTPStatus.OK, {"ok": True, "comments": list_forum_comments()})
            return
        if path == "/api/case-timeline":
            case_id = parse_qs(parsed.query).get("caseId", [""])[0]
            status, result = case_timeline(case_id)
            self.send_json(status, result)
            return
        if path == "/api/image-analysis-timeline":
            case_id = parse_qs(parsed.query).get("caseId", [""])[0]
            status, result = image_analysis_timeline(case_id)
            self.send_json(status, result)
            return

        self.serve_static(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self.read_json()
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "errors": [str(exc)]})
            return

        if path == "/api/calculate":
            result = compute_index(payload)
            status = HTTPStatus.OK if result["ok"] else HTTPStatus.UNPROCESSABLE_ENTITY
            self.send_json(status, result)
            return
        if path == "/api/assessments":
            status, result = save_assessment(payload)
            self.send_json(status, result)
            return
        if path == "/api/forum":
            status, result = save_forum_comment(payload)
            self.send_json(status, result)
            return
        if path == "/api/image-analysis":
            status, result = run_image_analysis(payload)
            self.send_json(status, result)
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"ok": False, "errors": ["API endpoint not found."]})

    def serve_static(self, path: str) -> None:
        if path == "/":
            self.path = "/index.html"
        else:
            decoded = unquote(path).lstrip("/")
            requested = (ROOT / decoded).resolve()
            if ROOT not in requested.parents and requested != ROOT:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            if requested.is_dir():
                self.path = f"/{decoded.rstrip('/')}/index.html"
            else:
                self.path = path

        if self.path.endswith(".js"):
            mimetypes.add_type("application/javascript", ".js")
        super().do_GET()


def main() -> None:
    init_db()
    port = 4173
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    print(f"Disfigurement Index prototype running at http://127.0.0.1:{port}")
    print(f"SQLite database: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
