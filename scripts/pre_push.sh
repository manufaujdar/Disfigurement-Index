#!/usr/bin/env bash
# Preserve native stdlib/frontend gates; synthetic checks create no clinical data.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
python3 -m py_compile server.py tests/test_algorithm.py tests/test_frontend_agent.py tools/frontend_agent/frontend_agent.py
node --check assets/js/app.js
node tests/display-settings.test.cjs
python3 tools/frontend_agent/frontend_agent.py audit --json
python3 -m unittest discover -s tools -p 'test_*.py'
npm audit --prefix tools/browser-tests --audit-level=high
node scripts/browser_regressions.cjs
python3 scripts/engineering_checks.py "$@"
