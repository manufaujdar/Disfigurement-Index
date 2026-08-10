# Local Healthcare-Safeguard Baseline

This project is research software. It is not HIPAA-certified, GDPR-certified,
FDA-cleared, CE-marked, or approved for production clinical use. Compliance
depends on the organization, jurisdiction, intended use, data, contracts, and
operating environment.

## Implemented Prototype Safeguards

- Local-first operation: the Python server binds to loopback and uses local
  SQLite.
- Data minimization: the calculator accepts concise case identifiers, structured
  domain scores, and optional notes; it should not receive unnecessary personal
  identifiers.
- No image upload: the Image AI page is a roadmap preview only.
- Input validation: scoring domains reject missing, out-of-range, malformed,
  non-object, and non-finite values.
- Auditability: saved assessments and forum comments write local audit events.
- Formula traceability: API responses include the algorithm version and
  research references.
- Review tooling: the local frontend agent checks accessibility, local links,
  research-boundary language, and security signals without external calls.

## Required Before PHI or Clinical Deployment

1. Define intended use, data classification, consent/authorization, retention,
   deletion, access roles, and incident response.
2. Perform documented privacy, security, clinical-safety, and regulatory risk
   reviews.
3. Add approved encryption at rest and in transit, managed identity, key
   rotation, backups, recovery testing, secure logging, and vulnerability
   scanning.
4. Establish minimum-necessary data handling, de-identification or limited data
   set rules, audit review, and any required BAA, DPA, IRB, ethics, or
   institutional approvals.
5. Validate the final Disfigurement Index formula, missing-data behavior,
   inter-rater reliability, intra-rater reliability, subgroup robustness, and
   clinical interpretation limits against appropriate reference methods.
6. Complete a model and dataset provenance review before any AI image-analysis
   feature is enabled.

Useful external guidance includes HHS HIPAA Security Rule materials, the HHS
Minimum Necessary Requirement, OWASP ASVS, and local institutional research
governance policies.
