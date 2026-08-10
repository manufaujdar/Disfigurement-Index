# Security and Privacy

This is research software, not a production clinical system. Do not commit
patient data, identifiers, screenshots containing clinical information,
photographs, access tokens, database dumps, private keys, or production
credentials.

If you find a security or privacy issue, do not publish sensitive details in a
public issue. Use a private maintainer channel or GitHub Security Advisories
when the repository is hosted. Include a minimal reproduction without protected
health information, credentials, or raw clinical captures.

Current prototype boundaries:

- The backend binds to `127.0.0.1` by default.
- SQLite data is local and ignored by Git.
- Browser fallback storage uses `localStorage`.
- The current Image AI page is a coming-soon page and does not upload or
  analyze images.
- The calculator stores structured case identifiers and notes only when the
  local user submits them.

Before any real clinical or PHI use, define access control, encryption,
retention, deletion, audit review, backups, vulnerability management, consent,
data-processing agreements, and incident-response responsibilities.
