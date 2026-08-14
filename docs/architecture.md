# System architecture

Disfigurement Index is a local-first browser and Python backend prototype. The
current architecture favors inspectability and synthetic/local use over hosted
clinical operation.

## Component flow

Browser pages -> JSON API in server.py -> validation and research-informed
algorithm -> local SQLite persistence -> calculator/history/forum responses.

When the backend is unavailable, selected browser routes use localStorage or
browser-local calculation. That fallback must remain visibly disclosed and must
not be mistaken for shared or clinical persistence.

## Components and data boundary

- server.py: static server, HTTP routes, validation, calculation, and SQLite access.
- index.html and assets/js/app.js: calculator and assessment workflow.
- about.html, privacy.html, forum.html, author.html: explanatory/feedback surfaces.
- image-analysis.html: roadmap preview only; no production image model is active.
- data/disfigurement_index.sqlite3: ignored local database.
- tools/frontend_agent: deterministic accessibility/research-boundary checks.
- tests/: algorithm and frontend-agent coverage.

The prototype is not an authenticated tenant system. Do not expose it to real
clinical data without identity, access control, encryption, retention,
migrations, audit review, and institutional approval.

## Non-goals

The calculator does not provide diagnosis, treatment advice, medico-legal
certainty, regulatory clearance, or automated image interpretation. Image AI
stays a coming-soon boundary until model/data cards, provenance, validation,
privacy review, human review, and approvals exist.

