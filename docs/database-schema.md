# Database Schema

Last updated: 2026-05-09

The prototype uses SQLite at `data/disfigurement_index.sqlite3`. The database is created automatically by `server.py` and is ignored by Git.

## Tables

### assessments

Stores saved calculator assessments.

- `id`
- `created_at`
- `clinician_name`
- `case_id`
- `clinical_setting`
- `anatomical_region`
- `notes`
- `score`
- `severity_band`
- `completeness`
- `confidence`
- `inputs_json`
- `result_json`

### forum_comments

Stores doctor feedback from the forum.

- `id`
- `created_at`
- `doctor_name`
- `topic`
- `comment`

### audit_events

Stores basic append-only audit records for important prototype actions.

- `id`
- `created_at`
- `event_type`
- `entity_type`
- `entity_id`
- `metadata_json`

## Production Migration Notes

Before deployment with real clinical data:

- Move from local SQLite to managed PostgreSQL, such as Supabase PostgreSQL or hospital-approved infrastructure.
- Add authenticated users, organization IDs, and row-level access rules.
- Encrypt sensitive fields and define retention policies.
- Add immutable audit-log review tooling.
- Add database migrations rather than automatic schema creation.
- Keep formula versions in controlled database records with approval metadata.
