# Contributing

Contributions are welcome as research-software improvements, subject to review
by the project owner.

Before opening a pull request:

1. Run `python3 -m unittest discover -s tests -v`.
2. Run `python3 -m py_compile server.py tests/test_algorithm.py tests/test_frontend_agent.py`.
3. Run `node --check assets/js/app.js`.
4. Run `python3 tools/frontend_agent/frontend_agent.py audit --json`.
5. Preserve the distinction between structured documentation and clinical
   diagnosis, treatment advice, medico-legal certainty, or regulatory status.
6. Use synthetic fixtures or explicitly approved de-identified research data.
   Never commit patient identifiers, clinical photographs, raw captures,
   credentials, private correspondence, or protected health information.
7. Document provenance and license terms for any third-party code, data, model,
   image, reference table, or clinical instrument introduced.

Contributors confirm that they have the right to submit their work under the
Apache-2.0 license. This project does not currently require a CLA or DCO, but
contributors remain responsible for copyright and data permissions.
