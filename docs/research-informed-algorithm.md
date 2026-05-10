# Research-Informed Development Algorithm

Last updated: 2026-05-09

## Status

This algorithm is a functional development scaffold. It is not the final validated Disfigurement Index formula and must not be represented as a clinically validated, medico-legal, or regulatory-approved scoring instrument.

The final formula should replace this scaffold after the completed research paper, scoring manual, validation data, and reference test cases are supplied.

## Why This Scaffold Exists

The website now needs a working backend and database. A realistic prototype should calculate from recognized clinical constructs rather than arbitrary mock fields. The current algorithm therefore uses domains repeatedly found in scar and appearance-disfigurement assessment literature:

- Scar quality domains: vascularity, pigmentation, thickness, relief, pliability, and surface area.
- Symptom burden: pain and itch or dysesthesia.
- Clinical impact: functional limitation.
- Contextual appearance impact: anatomical visibility and clinician global severity.
- Data quality: documentation confidence, reported separately from the severity score.

## Score Model

Each severity domain is scored from 1 to 10:

- 1 = normal, none, or least severe.
- 10 = worst severity in that domain.

The backend normalizes each domain to 0-1, multiplies by a fixed development weight, sums the weighted contributions, and returns a 0-100 base score. It then returns a clearly labeled context-adjusted score that applies a small anatomical-region visibility modifier. This is meant to make the prototype more clinically explainable, not to claim validation.

Documentation confidence is not part of the severity score. It is returned separately and generates a warning if low.

The result also returns:

- Grouped scores for scar/surface quality, extent/visibility, symptoms/function, and clinician synthesis.
- Top score drivers.
- Anatomical and clinical-setting context notes.
- Consistency warnings.
- Recommended review actions.

## Current Development Weights

- Vascularity: 0.09
- Pigmentation: 0.09
- Thickness / height: 0.10
- Relief / surface irregularity: 0.10
- Pliability / stiffness: 0.10
- Surface area / extent: 0.10
- Pain: 0.08
- Itch / dysesthesia: 0.06
- Functional limitation: 0.11
- Anatomical visibility: 0.10
- Clinician global severity: 0.07

Total = 1.00

These weights and context modifiers are intentionally transparent and editable. They are not statistically derived from your final validation dataset.

## Required Replacement Before Clinical Use

- Replace domain list and weights with the final research protocol.
- Add validated score bands and thresholds.
- Add test vectors from the research dataset.
- Add known edge cases and missing-data rules.
- Validate inter-rater reliability.
- Validate subgroup performance.
- Create a clinician-facing scoring manual.
- Add formal version approval and release notes.

## Research Basis Used

- POSAS official site: https://www.posas.nl/
- Rasch analysis of POSAS in burn scars: https://link.springer.com/article/10.1007/s11136-011-9924-5
- Scar Assessment Tools review: https://pmc.ncbi.nlm.nih.gov/articles/PMC8260845/
- Review of Scar Scales and Measuring Devices: https://pmc.ncbi.nlm.nih.gov/articles/PMC2890387/
- Modified Vancouver Scar Scale linked with TBSA: https://pubmed.ncbi.nlm.nih.gov/23433706/
- Derriford Appearance Scale paper: https://www.derriford.info/Downloadableresources/DAS59%20DLH%20ATC.pdf
