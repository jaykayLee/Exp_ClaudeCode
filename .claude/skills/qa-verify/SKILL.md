---
name: qa-verify
description: Run the full verification set for the Naver Blog automation project and report honest results (counts, exit codes, environment, what was NOT run). Use at the end of every phase, before packaging, after any change to tools/, 02_CORE, 03_PROVIDERS, 06_UI or 11_ADDONS, or when the user asks "검증", "테스트", "QA".
---

# QA verify

Run from the repo root. Save every log under `00_SESSION/evidence/<PHASE>/`.

| # | Check | Command | Expect |
|---|---|---|---|
| 1 | Unit + integration (workspace + add-on) | `cd workspace/Naver_Blog_Automation && .venv/bin/python tools/qa_runner.py` | `OK`; read `09_LOGS/test_report.json` `suites` |
| 2 | Doctor | `.venv/bin/python tools/doctor.py` | exit 0, `local_ok: true` |
| 3 | Daily run | `.venv/bin/python tools/run_once.py` then `--snapshot-demo` | NO_INPUT exit 0; demo DONE/DEMO_ONLY |
| 4 | Existing UI QA (browser) | `.venv/bin/python 00_PROJECT/QA/developer_ui_qa.py` | `passed` 15+, `javascript_errors: []` |
| 5 | Panel E2E (browser) | `.venv/bin/python ../../00_SESSION/evidence/P04/ui_snapshot_e2e.py` | all PASS |
| 6 | Clean install | `tools/build_release.py --out <tmp outside repo>`; unzip into a path with space+Korean; venv → lock → `pip check` → doctor → qa_runner → reinstall keeps `settings.local.json` | all pass |
| 7 | Handoff integrity | `python3 tools/verify_release.py` (repo root) | PASS (regenerate the manifest if docs changed) |
| 8 | CI (if pushed) | GitHub Actions `ci` linux + windows | both green; download artifacts |

Notes
- Browser checks need dev-only Playwright (installed by `scripts/cloud_session_setup.sh`); Chromium: `/opt/pw-browsers/chromium` in cloud, else default. The panel CSP blocks eval → use `bypass_csp=True` in test contexts only.
- Run tests in temp copies; never leave demo outputs in the real workspace.

## Report format
For each check: command, exit code, counts (executed/failed/errors), log path. Then a separate list "NOT RUN" (Windows PC, real Danawa page, Naver Shopping, Naver editor paste, publication). Never copy numbers from older docs; a check that did not run is `NOT_RUN` with 0 passed. If a test fails, show the assertion and fix the cause, not the test, unless the test itself was wrong (say which).
