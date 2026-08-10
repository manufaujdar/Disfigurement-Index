# Open-Source Extension Boundary

Future extensions should remain modular and reviewable.

Allowed extension types:

- Alternative validated scoring formulas behind explicit version gates.
- Import/export adapters for de-identified research datasets.
- Optional AI image-analysis adapters with model cards, dataset cards,
  provenance, and validation records.
- Accessibility, internationalization, reporting, and documentation
  improvements.

Do not commit:

- Patient photographs or identifiable clinical records.
- Raw PHI, production database exports, or credentials.
- Unverified model weights or datasets without provenance.
- Vendor SDK binaries unless redistribution rights are documented.
- Changes that imply diagnostic, treatment, medico-legal, or regulatory status
  without formal approval.
