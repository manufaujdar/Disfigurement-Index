## Summary

Describe the change and why it belongs in the Disfigurement Index prototype.

## Validation

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -m py_compile server.py tests/test_algorithm.py tests/test_frontend_agent.py tools/frontend_agent/frontend_agent.py`
- [ ] `node --check assets/js/app.js`
- [ ] `python3 tools/frontend_agent/frontend_agent.py audit --json`
- [ ] Browser smoke test completed if the website changed

## Safety and Provenance

- [ ] No patient data, identifiers, credentials, or protected captures included
- [ ] No diagnostic, treatment, medico-legal, or regulatory claim added
- [ ] Third-party code, models, data, and assets have documented licenses
- [ ] Formula, AI, dataset, or image-analysis changes include relevant card and validation updates
