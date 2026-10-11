# Main-push engineering checks

Run the native stdlib/frontend tests, synthetic browser flow and exact outgoing
commit check together. Python runtime dependencies remain stdlib-only.

```bash
npm ci --prefix tools/docs-tools --ignore-scripts
npm ci --prefix tools/browser-tests --ignore-scripts
tools/browser-tests/node_modules/.bin/playwright install chromium
bash scripts/pre_push.sh --base origin/main
```

The browser profile pins Playwright 1.63.0 as an isolated development tool, with
a resolved dependency audit. It serves static pages locally, aborts all API and
external requests, and never starts the SQLite/clinical server. Synthetic fields
exercise large text, reduced motion, failed saves, retained form input, result
focus and preserved reading position. Existing clinical and research boundaries
remain unchanged. CI uses public Python/JavaScript CodeQL analysis.

## Before pushing

Use Betterleaks 1.8.1, actionlint 1.7.12, zizmor 1.30.1 and markdownlint-cli
0.49.1 on PATH, Node >=24.15 for docs tools (CI pins24.21.0) and Python >=3.10 alongside the declared runtime.
Preserve native hooks/core.hooksPath; no hook replacement is installed here.

```sh
npm ci --prefix tools/docs-tools --ignore-scripts
npm ci --prefix tools/browser-tests --ignore-scripts
tools/browser-tests/node_modules/.bin/playwright install chromium
bash scripts/pre_push.sh --base origin/main
```

Fetch current main first. `--base` resolves to an immutable ancestor commit.
For pre-commit checks use `--working`, which explicitly skips commit-range secrets.
Complete staged-secret/native commit gates, then rerun on a clean tree without
`--working` and push the exact checked HEAD normally to main. Dirty trees and
HEAD changes fail; initial pushes explicitly scan all reachable history.
Post-push checks cannot prevent an already-landed commit. No auto-fix/push or deploy
loop is enabled. Fetch/recheck if concurrent main changes make the push fail.

## Tool provenance and limits

- [Betterleaks](https://github.com/betterleaks/betterleaks), MIT: redacted detection
  only, no live validation or revocation. All newly reachable ancestors are scanned.
- [actionlint](https://github.com/rhysd/actionlint) and
  [zizmor](https://github.com/zizmorcore/zizmor), MIT: workflow syntax/types and
  offline permission/injection/supply-chain checks. Linux binary downloads use
  pinned upstream release-asset SHA-256s in `tools/install_ci_tools.py`.
- [markdownlint-cli](https://github.com/igorshubovych/markdownlint-cli), MIT:
  scoped syntax/whitespace rules on changed root engineering docs and `docs/`
  Markdown. The repo-owned locked tool profile includes advisory patches.
  [lychee](https://github.com/lycheeverse/lychee), MIT/Apache-2.0, 0.24.2 checks
  offline links. Relative files within the repo are checked offline. Remote URLs,
  external workspace references and research/vendor/clinical corpora are not
  visited or reformatted; existing semantic validators retain authority.
- [Playwright](https://github.com/microsoft/playwright), Apache-2.0, 1.63.0:
  local synthetic browser regressions. API and external requests are aborted; static
  fixture files stay local. `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` can select a
  trusted existing Chrome; otherwise install Chromium. Screen readers and
  physical devices remain unverified.
- Both isolated development profiles audit locked dependencies at the high
  severity threshold; metadata goes to npm's advisory service. No forced fixes
  or threshold reductions are used.

A green commit certifies these checks only; existing consent, clinical, model,
privacy and governed release boundaries still apply. Rollback removes added
checks/jobs without changing native checks or product contracts.

## Optional CodeRabbit scope preparation

`python3 tools/coderabbit_review.py --base <previous-main-SHA>` verifies the exact
committed main scope without a model call. The manual scope workflow does the
same. CLI 0.9.0 is installed locally but account status is `not_authenticated`.
Actual hosted review requires separate explicit `--execute`, authenticated
assigned-seat access and its allowance policy; it is advisory and does not fix
or push. No automatic cloud review is enabled and no credential is committed.

The native hook dispatcher calls `python3 scripts/native_pre_push.py` with Git's
original pre-push stdin. It passes the exact remote main SHA to the quality
command, rejects a different outgoing HEAD or extra/non-main refs, and explicitly
handles an initial all-zero remote SHA. Existing hooks and `core.hooksPath` are
preserved. The `origin/main` command above is an explicit manual fallback after
fetching; the hook never substitutes that potentially stale ref for Git's SHA.
