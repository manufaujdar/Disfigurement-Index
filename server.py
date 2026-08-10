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
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "disfigurement_index.sqlite3"
ALGORITHM_VERSION = "research-informed-composite-v1.1"

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


def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
    with db() as conn:
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
                str(payload["caseId"]).strip(),
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
            {"algorithmVersion": ALGORITHM_VERSION, "score": result["score"]},
        )

    result["assessmentId"] = assessment_id
    result["createdAt"] = created_at
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
            self.send_json(status, {"ok": contract["ok"], "time": now_iso(), "algorithmVersion": ALGORITHM_VERSION, "algorithmContract": contract})
            return
        if path == "/api/config":
            self.send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "algorithmVersion": ALGORITHM_VERSION,
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
