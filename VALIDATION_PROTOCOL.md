# Disfigurement Index Validation Plan

This is a research protocol scaffold, not evidence that the Disfigurement Index
is clinically validated. Use only synthetic, test, or ethics-approved
de-identified data until the responsible study team approves otherwise.

## Scoring Formula

1. Freeze the algorithm version, domain wording, weights, severity bands,
   anatomical context modifiers, confidence rules, and missing-data rules.
2. Create reference test cases that cover low, mid, high, boundary, malformed,
   and discordant inputs.
3. Test score stability across supported Python versions and browser fallback
   calculation paths.
4. Document every formula change in `CHANGELOG.md` and the algorithm/model
   card before release.

## Reliability

1. Measure inter-rater and intra-rater reliability across relevant clinical
   specialties and settings.
2. Report agreement and uncertainty for total score, severity band, and domain
   subscores.
3. Stratify results by anatomical region, disfigurement type, documentation
   quality, skin tone, age group where appropriate, and clinical setting.
4. Define adjudication and repeat-scoring rules before looking at outcomes.

## Clinical Interpretation

1. Define intended use and non-use cases before any patient-facing study.
2. Compare against appropriate reference instruments, clinician global
   assessment, and patient-reported appearance/functional measures.
3. Report sensitivity to missing data, documentation quality, and follow-up
   capture conditions.
4. Do not use scores for diagnosis, treatment decisions, benefit claims,
   medico-legal conclusions, or regulatory claims without separate approval.

## AI Image Analysis

1. Keep image analysis disabled until a model/version, dataset card,
   preprocessing policy, uncertainty method, and human-review workflow exist.
2. Split validation data by subject, not image. Maintain a held-out test set.
3. Report segmentation, localization, calibration, and subgroup robustness
   metrics with confidence intervals.
4. Store model provenance, checkpoint hashes, prompt policy, and failure modes.
5. Require clinician review of every AI-assisted observation before it can
   influence a saved case or report.
