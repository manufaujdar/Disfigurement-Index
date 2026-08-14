# Technical overview

Status: local-first research prototype.

## Runtime and code map

- Python 3.10 or newer; standard-library backend in server.py.
- Static HTML/CSS/JavaScript pages under the repository root and assets/.
- SQLite database path is data/disfigurement_index.sqlite3 and is Git-ignored.
- tools/frontend_agent provides deterministic local frontend review.
- tests/ covers algorithm behavior and frontend-agent checks.
- pyproject.toml declares no runtime dependencies.

## API and algorithm

The backend exposes health/configuration, calculation, assessment persistence,
and forum read/write routes. README.md is the route inventory. server.py holds
research-informed domains, weights, bands, an algorithm version, and literature
links. Keep response fields, evidence IDs, score provenance, formula version,
and test vectors inspectable when this changes.

## Verification

Run unittest discovery, Python compilation, JavaScript syntax checking, and
the frontend-agent audit as documented in README.md. Add regression fixtures for
missing fields, non-finite numbers, wrong ranges, version changes, escaping,
local fallback disclosure, and safety copy.

## Production gaps

Authentication, tenant isolation, encrypted storage, retention, managed
migrations, immutable audit review, clinical validation, consent, image
analysis, and institutional/regulatory approvals are absent or future work.
Future images, model weights, and third-party assets need separate rights and
provenance records.

