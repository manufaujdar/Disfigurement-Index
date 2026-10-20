# Documentation index

Disfigurement Index is an Apache-2.0 local-first clinical research prototype
for structured, doctor-led documentation. It is not a diagnostic or treatment
product, and its current score is a research-informed scaffold rather than a
validated clinical index.

## Choose a task

| Task | Read first | Continue with |
| --- | --- | --- |
| Run the prototype or inspect routes | [Local run and pages](../README.md#run-locally) | [Technical overview](technical-overview.md) |
| Change the API or persistence | [Architecture](architecture.md) | [Database schema](database-schema.md), [security policy](../SECURITY.md) |
| Change calculation behavior | [Algorithm rationale](research-informed-algorithm.md) | [Validation protocol](../VALIDATION_PROTOCOL.md), [algorithm card](../ALGORITHM_CARD_TEMPLATE.md) |
| Assess future image-analysis work | [Prototype requirements](prototype-requirements.md) | [Extension policy](../OPEN_SOURCE_EXTENSIONS.md), [dataset card](../DATASET_CARD_TEMPLATE.md) |
| Contribute or publish | [Contribution guide](../CONTRIBUTING.md) | [Engineering checks](../TOOLING.md), [governance](../GOVERNANCE.md), [compliance](../COMPLIANCE.md) |

## File and folder ownership

| Location | Purpose |
| --- | --- |
| Root HTML pages | Calculator, guide, feedback, author, privacy and image-analysis preview routes |
| `assets/css/`, `assets/js/` | Shared browser styles and application behavior |
| `server.py` | Local Python API and SQLite boundary |
| `docs/` | Architecture, data model, algorithm rationale and product plans |
| `tests/` | Deterministic backend, static-path and browser-state regressions |
| `scripts/`, `tools/` | Engineering gates, browser checks and supervised frontend tooling |
| `data/` | Ignored local SQLite runtime records; never a source or fixture directory |
| Root governance documents | Shared clinical, privacy, validation, licensing and contribution requirements |

Keep new browser assets under `assets/`, synthetic fixtures with their tests,
and design or methodology notes under `docs/`. Preserve the root HTML routes
and shared legal entry points when improving navigation.

## Evidence and release limits

The calculator remains a research scaffold and the Image AI page remains a
roadmap preview. Literature such as POSAS/Vancouver does not transfer validated
weights or clinical claims to this implementation. Real data, algorithm changes,
image interpretation and deployment need the owning validation and governance
reviews. See [LICENSE](../LICENSE), [NOTICE](../NOTICE) and
[COMPLIANCE.md](../COMPLIANCE.md) for source and data boundaries.

