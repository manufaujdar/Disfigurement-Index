# Disfigurement Index Website Prototype

Disfigurement Index is a local-first, open-source clinical research prototype
for structured doctor-led disfigurement documentation. It includes a calculator,
local SQLite persistence, a doctor-feedback forum, governance pages, and a
local AI-assisted image-analysis page.

This repository is located at:

```text
/Users/manufaujdar/Disfigurement Index
```

The related reference project reviewed for open-source governance patterns is:

```text
/Users/manufaujdar/Documents/Manu/clinical-lidar-framework
```

## Research Boundary

This project is not a diagnostic medical product. It does not provide
treatment advice, medico-legal certainty, regulatory clearance, clinical
validation, or automated image interpretation. The current algorithm is a
research-informed development scaffold until the completed Disfigurement Index
protocol, validated weights, severity bands, missing-data rules, and reference
test cases are supplied.

No clinical validation or diagnostic status is implied by this prototype.

The Image AI page performs local computer-vision analysis for structured visual
review support. It does not diagnose, classify disease, replace clinician
review, or store source images.

## What Is Included

- Backend JSON API built with the Python standard library.
- SQLite database for local assessment and forum records.
- Research-informed calculation scaffold with explicit algorithm versioning.
- Case-level follow-up tracking with score delta, direction, and recent timeline.
- Local camera/photo image analysis with quality checks, visual segmentation,
  overlay preview, image-derived domain suggestions, and calculator handoff.
- Fail-closed checks for malformed domain payloads, out-of-range values, and
  non-finite scoring inputs.
- Calculator, guide, forum, author, governance, and Image AI pages.
- Browser-local fallback calculation and local comment/history storage when the
  backend is unavailable.
- Downloadable and copyable calculator summaries.
- Local deterministic frontend review agent.
- Open-source governance, contribution, security, compliance, citation, and
  validation documentation.

## Run Locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python server.py 4173
```

Open:

```text
http://127.0.0.1:4173
```

The local SQLite database is created automatically at:

```text
data/disfigurement_index.sqlite3
```

The `data/` directory is ignored by Git.

## Pages

- `index.html` - calculator and local assessment save workflow.
- `image-analysis.html` - camera/photo AI image-analysis workflow.
- `about.html` - clinical-use guide.
- `forum.html` - doctors feedback forum stored in SQLite or localStorage.
- `author.html` - author and contributor details.
- `privacy.html` - data governance and prototype privacy boundaries.

## API

- `GET /api/health`
- `GET /api/config`
- `GET /api/case-timeline?caseId=CASE-ID`
- `GET /api/image-analysis-timeline?caseId=CASE-ID`
- `POST /api/calculate`
- `POST /api/assessments`
- `POST /api/image-analysis`
- `GET /api/forum`
- `POST /api/forum`

## Quality Gates

Run all checks from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile server.py tests/test_algorithm.py tests/test_frontend_agent.py tools/frontend_agent/frontend_agent.py
node --check assets/js/app.js
.venv/bin/python tools/frontend_agent/frontend_agent.py audit --json
```

The frontend review agent checks static accessibility signals, local links,
focus styles, research-boundary language, persistence disclosure, and dynamic
HTML escaping. It does not call external models or upload source files.

## Governance and Validation

Before real clinical data, public deployment, or clinical use of image analysis, review:

- `VALIDATION_PROTOCOL.md`
- `COMPLIANCE.md`
- `SECURITY.md`
- `GOVERNANCE.md`
- `ALGORITHM_CARD_TEMPLATE.md`
- `DATASET_CARD_TEMPLATE.md`
- `OPEN_SOURCE_EXTENSIONS.md`

Never commit patient data, identifiable photographs, raw clinical captures,
credentials, private research material, production database exports, model
weights, or proprietary SDK binaries without documented rights and explicit
approval.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
