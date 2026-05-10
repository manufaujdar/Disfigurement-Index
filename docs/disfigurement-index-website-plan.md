# Disfigurement Index Website Plan

Last updated: 2026-05-09

## 1. Product Positioning

Build the Disfigurement Index as a doctor-only clinical calculation and documentation system, not a public self-diagnosis website. The product should help qualified clinicians calculate, review, explain, and document a validated disfigurement index using the research protocol that will be supplied later.

Until regulatory review confirms otherwise, treat the product as potential clinical decision support and possibly Software as a Medical Device (SaMD), because it may compute risk scores, severity scores, probabilities, recommendations, or structured clinical outputs. FDA guidance states that risk scores, probabilities, time-critical outputs, or outputs without a clear basis may remain regulated device functions, while simple routine calculations may receive lower regulatory scrutiny when clinicians can independently verify them.

Core promise:

- Reliable scientific calculation.
- Transparent clinical reasoning.
- Strong auditability.
- Doctor-controlled interpretation.
- Privacy, security, and regulatory readiness from day one.

Non-goals for the first version:

- Patient self-assessment.
- Automated diagnosis.
- Treatment directives without physician review.
- Image-based AI scoring unless separately validated and regulated.
- Adaptive model updates in production without formal change control.

## 2. Primary Users

### Clinician

- Creates patient or case assessment.
- Enters structured findings.
- Reviews calculated index score and score drivers.
- Compares repeated assessments over time.
- Exports a signed clinical report.

### Specialist Reviewer

- Reviews borderline or high-impact cases.
- Adds second-opinion annotations.
- Confirms or disputes individual scoring domains.
- Locks final score version.

### Research / Clinical Governance Team

- Maintains formula versions.
- Uploads validated evidence references.
- Reviews aggregate performance and feedback.
- Monitors calculation drift, edge cases, and data quality.

### Admin / Compliance Officer

- Manages organizations, roles, permissions, consent templates, audit logs, and data-retention settings.

## 3. Recommended Website Structure

### Public Site

The public site should be restrained and professional. It should explain the purpose, research basis, doctor-only access, validation status, and institutional onboarding path. It should not expose a public calculator.

Pages:

- Home: concise explanation of the Disfigurement Index, doctor-only positioning, research-backed calculation, and validation status.
- Research: summary of methodology, citations, validation cohorts, limitations, and publication status.
- Clinical Use: intended use, contraindications, required inputs, interpretation boundaries, and report examples.
- Security and Compliance: privacy model, encryption, audit logging, hosting posture, and regulatory readiness.
- Request Access: institution or clinician onboarding form.
- Contact / Governance: medical advisory board, version history, and support channels.

### Authenticated Doctor Portal

The doctor portal should be the main product.

Core screens:

- Dashboard: active cases, pending reviews, recent assessments, score distribution, and alerts for incomplete data.
- New Assessment Wizard: guided structured input with validation at each step.
- Patient / Case Record: demographics, injury / condition details, prior assessments, attachments, notes, and consent state.
- Index Calculator: domain-by-domain scoring, live calculation, uncertainty flags, and formula version.
- Evidence Panel: why each domain contributes to the score, source references, assumptions, and missing-data handling.
- Longitudinal View: score changes over time, intervention milestones, and report comparisons.
- Report Builder: clinician-approved PDF/HTML report with score, inputs, interpretation notes, limitations, formula version, and reviewer signatures.
- Review Queue: second-opinion workflow for high-risk, ambiguous, or disputed cases.
- Admin Console: users, organizations, roles, audit logs, formula releases, feature flags, and data retention.

## 4. Suggested First-Viewport Design

### Public Home

Visual direction:

- Clean medical-scientific interface, not a marketing-heavy landing page.
- White or very light neutral base, deep teal or clinical blue as an accent, warm warning color only for clinical flags.
- Clear typography, dense information, and minimal decoration.

First screen:

- Header: Disfigurement Index, Research, Clinical Use, Security, Request Access.
- Main headline: "Disfigurement Index"
- Supporting copy: "A doctor-only clinical scoring platform for structured assessment, transparent calculation, and auditable reporting."
- Primary action: "Request clinical access"
- Secondary action: "Review methodology"
- Trust strip: "Formula versioning", "Clinician review required", "Audit-ready reports", "Privacy-first architecture"
- Below fold preview: screenshot-style product panel showing an assessment dashboard, not a decorative hero.

### Doctor Portal

The first authenticated screen should be a work surface:

- Left sidebar: Dashboard, Cases, New Assessment, Reviews, Reports, Evidence, Admin.
- Top bar: organization, environment/version, user role, support.
- Main grid: pending assessments, review queue, score trend card, recent reports.
- Right rail: protocol updates, formula version alerts, missing data warnings.

## 5. Calculation and Scientific Reliability Model

The calculation engine should be separate from the user interface. The UI should never contain clinical formula logic.

### Calculation Engine Requirements

- Version every formula, coefficient, threshold, and interpretation rule.
- Store immutable calculation inputs and outputs.
- Return a full explanation object, not only a final score.
- Support unit validation, allowed ranges, required fields, and missingness rules.
- Include deterministic rounding and precision rules.
- Include reference test vectors from the research team.
- Generate reproducible results across environments.
- Keep deprecated formulas available for old reports.
- Require formal approval before a new formula becomes active.

### Output Should Include

- Final index score.
- Severity band, if validated.
- Domain-level contributions.
- Missing or uncertain input flags.
- Formula version and release date.
- Clinical interpretation boundaries.
- Evidence citations linked to each domain.
- Reviewer / signer identity and timestamp.

### Model Governance

If the index later includes AI/ML:

- Use locked model versions in production.
- Maintain model cards and performance summaries.
- Track training data provenance and inclusion/exclusion criteria.
- Validate performance by subgroup, including age, sex, skin tone where applicable, anatomical region, etiology, and institution.
- Monitor real-world performance without automatically retraining production models.
- Use predetermined change-control planning before model updates.

## 6. Clinical Validation Plan

Reliability should be proven before the website is positioned as clinical-grade.

Evidence package to prepare:

- Intended use statement.
- Target users and clinical setting.
- Exact score definition.
- Data dictionary and scoring manual.
- Derivation dataset description.
- Internal validation.
- External validation.
- Inter-rater and intra-rater reliability.
- Measurement error and confidence interval strategy.
- Subgroup performance and bias analysis.
- Handling of missing, uncertain, or conflicting data.
- Comparison against existing clinical or medico-legal assessment methods, if any.
- Clinical utility statement: how the score changes documentation, review, triage, follow-up, or outcome tracking.
- Limitations and contraindications.

Acceptance criteria examples:

- Formula unit tests pass against research reference cases.
- Independent clinician reviewers reproduce scores within an agreed tolerance.
- External validation meets predefined calibration and discrimination targets where applicable.
- Reports always show formula version and required limitations.
- High-impact outputs require clinician confirmation before finalization.

## 7. Recommended Technical Architecture

### Best Initial Architecture

Use a modular monolith with a separately packaged calculation engine. This is easier to validate and audit than early microservices, while still allowing future separation.

Components:

- Frontend: Next.js with TypeScript.
- API backend: NestJS or FastAPI.
- Calculation engine: isolated TypeScript or Python package, depending on the research team's statistical tooling.
- Database: PostgreSQL.
- File storage: encrypted object storage for reports and clinical attachments.
- Queue: Redis or managed queue for report generation, imports, and notifications.
- Auth: OpenID Connect / SAML for hospital SSO, plus MFA.
- Observability: structured logs, metrics, traces, uptime checks, and calculation-error alerts.
- Infrastructure: Dockerized services, Terraform-managed cloud resources, CI/CD with approvals.

For a medical calculation product, FastAPI plus a Python calculation package is often practical if the research model is in Python/R/statistical tooling. Next.js remains a strong frontend choice. If all logic is simple deterministic arithmetic, TypeScript across frontend/backend can reduce language split, but formula logic must still live only in the backend calculation package.

### Data Flow

1. Doctor creates or opens a case.
2. UI collects structured inputs.
3. API validates permissions and schema.
4. Calculation engine runs the active formula version.
5. Backend stores immutable calculation record.
6. UI displays score, drivers, warnings, and evidence.
7. Doctor confirms interpretation.
8. Report service generates signed report.
9. Audit log records all access, changes, exports, and formula versions.

### Suggested Domain Model

- Organization
- User
- Role
- Patient or De-identified Case
- Consent / Authorization
- Assessment
- AssessmentInput
- CalculationRun
- FormulaVersion
- EvidenceReference
- Review
- Report
- Attachment
- AuditEvent
- ClinicalFeedback

## 8. Privacy and Security Requirements

Minimum baseline:

- Role-based access control by organization and clinical role.
- MFA for all users.
- Encryption in transit and at rest.
- Field-level protection for sensitive identifiers where possible.
- Immutable audit trail for read, write, export, and admin actions.
- Session timeout and device/session management.
- Least-privilege service accounts.
- Secure backup and restore drills.
- Vulnerability scanning and dependency monitoring.
- Incident response plan.
- Data retention, deletion, and legal hold policies.
- Separate environments for development, staging, validation, and production.
- No real patient data in development.

Jurisdiction planning:

- United States: HIPAA may apply if the product handles protected health information for covered entities or business associates.
- India: Digital Personal Data Protection Act, 2023 obligations should be mapped before collecting identifiable patient data.
- European Union / United Kingdom: GDPR and medical-device rules may apply if deployed there.
- Global clinical deployments: map intended use and device classification per target market before launch.

## 9. Quality, Regulatory, and Audit Framework

Build the project as if it will need medical-device evidence, even during prototype.

Required controlled documents:

- Intended use.
- Software requirements specification.
- Clinical requirements.
- Risk management file.
- Data dictionary.
- Calculation specification.
- Verification and validation plan.
- Traceability matrix.
- Cybersecurity plan.
- Usability engineering plan.
- Release notes and version history.
- Change-control log.
- Clinical evaluation report.
- Post-market / real-world monitoring plan.

Recommended standards and guidance alignment:

- FDA Clinical Decision Support Software guidance.
- FDA Software as a Medical Device resources.
- FDA Content of Premarket Submissions for Device Software Functions.
- FDA QMSR / ISO 13485 alignment.
- IMDRF SaMD key definitions and clinical evaluation.
- IEC 62304 for medical device software lifecycle.
- ISO 14971 for risk management.
- HL7 FHIR for interoperability.
- NIST Cybersecurity Framework 2.0 for cybersecurity governance.

## 10. Advanced Medical Uses to Plan For

These should be phased in only after validation:

- Longitudinal monitoring of disfigurement severity over time.
- Structured medico-legal documentation support.
- Pre- and post-treatment comparison reports.
- Multidisciplinary review boards.
- Research registry mode using de-identified cases.
- Institution-level quality dashboards.
- Inter-rater reliability studies inside the platform.
- FHIR integration with hospital EHR systems.
- Optional image annotation workflow for clinician-drawn regions, without automated image scoring at first.
- Future AI image assistance only after separate validation, regulatory review, and bias testing.

## 11. Phased Delivery Plan

### Phase 0: Research Intake and Requirements

- Collect the research paper, formulas, scoring domains, validation data, and intended use.
- Define clinical scope, exclusions, and report language.
- Create the calculation specification and reference cases.
- Decide regulatory target markets.

### Phase 1: Non-Clinical Prototype

- Build public website and doctor portal shell.
- Implement fake/sample data only.
- Build assessment wizard and report layout.
- Build calculation engine interface with a clearly labeled research-informed development scaffold until the validated formula is supplied.
- Create audit-log architecture early.

### Phase 2: Validated Calculator MVP

- Implement real formulas.
- Add test vectors from research.
- Add formula versioning.
- Add clinician review workflow.
- Add PDF report generation.
- Complete security baseline.

### Phase 3: Clinical Pilot

- Run with selected doctors and de-identified or approved patient data.
- Measure usability, scoring reproducibility, missing-data frequency, and report acceptance.
- Add external validation dataset support.
- Lock release candidate for clinical use.

### Phase 4: Regulated / Production Release

- Complete regulatory classification review.
- Complete clinical evaluation and software validation package.
- Deploy on compliant infrastructure.
- Establish support, incident response, and post-market monitoring.

## 12. Immediate Next Decisions

Before implementation starts, collect:

- The exact formula or statistical model.
- Required input fields and scoring domains.
- Units, scales, and valid ranges.
- Sample completed cases.
- Desired report format.
- Country or countries of launch.
- Whether patient identifiers will be stored.
- Whether images will be uploaded.
- Whether the platform is for clinical care, research only, medico-legal documentation, or all three.

## 13. Source Baseline

- FDA Clinical Decision Support Software FAQ: https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs
- FDA Software as a Medical Device: https://www.fda.gov/medical-devices/digital-health-center-excellence/software-medical-device-samd
- FDA Content of Premarket Submissions for Device Software Functions: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/content-premarket-submissions-device-software-functions
- FDA Quality Management System Regulation: https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- FDA Good Machine Learning Practice: https://www.fda.gov/medical-devices/software-medical-device-samd/good-machine-learning-practice-medical-device-development-guiding-principles
- IMDRF SaMD Clinical Evaluation: https://www.imdrf.org/documents/software-medical-device-samd-clinical-evaluation
- IMDRF SaMD Key Definitions: https://www.imdrf.org/documents/software-medical-device-samd-key-definitions
- HL7 FHIR specification: https://www.hl7.org/fhir/
- HHS HIPAA Security Rule summary: https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html
- NIST Cybersecurity Framework 2.0: https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20
- CDSCO Medical Device and Diagnostics: https://www.cdsco.gov.in/opencms/opencms/en/Medical-Device-Diagnostics/
- India Digital Personal Data Protection Act, 2023: https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023.pdf
