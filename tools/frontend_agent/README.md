# Disfigurement Index frontend review agent

This local review agent audits the static frontend and prepares a bounded
improvement brief for future supervised AI-assisted work. It does not call an
external model, upload source files, edit code, or commit changes.

Run from the repository root:

```bash
python3 tools/frontend_agent/frontend_agent.py audit
python3 tools/frontend_agent/frontend_agent.py audit --json
python3 tools/frontend_agent/frontend_agent.py compare --json
python3 tools/frontend_agent/frontend_agent.py prompt > /tmp/disfigurement-index-frontend-brief.txt
```

The audit checks page landmarks, headings, skip links, active navigation,
broken local links, image alt text, form label coverage, focus styles,
dynamic-HTML escaping, persistence disclosure, and research-only safety
language.

Do not pass patient photographs, identifiers, clinical notes, credentials, or
unpublished research records to an external agent. Keep AI image-analysis work
behind provenance, validation, and human-review gates.
