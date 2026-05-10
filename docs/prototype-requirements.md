# Prototype Requirements

Last updated: 2026-05-09

## Current Scope

Create a lightweight doctor-facing website prototype for the Disfigurement Index. The current version includes a local backend, SQLite database, API-backed calculator, saved assessments, and database-backed feedback forum.

## Pages

- Home: index form details, backend calculator, result interpretation, and clinical workflow summary.
- About and Guide: website purpose, clinical-use guide, intended-use boundaries, research paper link area, evidence references, and validation checklist.
- Doctors Forum: database-backed prototype discussion board for clinical feedback and implementation comments.
- Author: author profile section, affiliations, contribution statement, and contact area with placeholders for final details.
- Data Governance: prototype privacy and data management boundaries.

## Medical Safety Requirements

- The calculator must clearly state that its formula is a research-informed development scaffold until the validated research formula is provided.
- Any clinical score output must show version, assumptions, missing-data warnings, and clinician-review language.
- The public prototype must not invite patient self-diagnosis.
- The design must communicate doctor-only use, clinical auditability, and research governance.

## Technical Requirements

- No external runtime dependency for the prototype.
- Python standard-library backend with SQLite.
- Static HTML, CSS, and JavaScript frontend.
- Shared responsive design across all pages.
- Calculator logic isolated in backend Python and easy to replace with the validated formula.
- Forum comments stored in SQLite.
- Research paper URL, source references, and author details must be easy to update.

## Deferred Requirements

- Doctor authentication and role-based access control.
- Persistent forum database.
- Case storage and patient identifiers.
- Report generation.
- Formula version approval workflow.
- Audit logs.
- Vercel deployment.
- Supabase or other managed backend.
- Clinical validation data import.
- Regulatory classification review.

## Backend Recommendation For Next Phase

For the next phase, add:

- Vercel or equivalent static/frontend hosting.
- Supabase PostgreSQL for doctors forum, author/research metadata, calculation audit records, and eventually de-identified pilot cases.
- Server-side formula engine with versioned formulas and test vectors.
- Authentication with MFA and organization-level roles before real clinical data is entered.
