---
name: windows-ci-triage
description: Diagnose and fix Windows problems for the Naver Blog automation project from GitHub Actions `ci` windows logs or from the user's 09_LOGS / WINDOWS_ACCEPTANCE.md results (P07). Use when CI windows is red, the user reports a BAT window error, install.bat fails, Korean text is garbled, or the scheduled task does not run.
---

# Windows CI / PC triage

## Gather
- CI: `gh run list --workflow ci`, `gh run view <id> --log-failed`, download artifact `windows-logs` (contains `09_LOGS/install_*.log`, `test_report.json`, `doctor_report.json`, `daily/`).
- User PC: `09_LOGS/` folder + ticked `00_PROJECT/QA/WINDOWS_ACCEPTANCE.md` (sections A–F).
- Note which evidence it is: CI runner (clean Windows Server) ≠ user PC. Update status fields separately.

## Common causes → fixes
| Symptom | Likely cause | Fix |
|---|---|---|
| `'…' is not recognized`, broken lines | BAT lost CRLF or got non-ASCII bytes | keep BAT ASCII + CRLF (`.gitattributes` `* -text`); `10_TESTS/test_daily_ops.py` guards this |
| Path with space/Korean fails | unquoted `%~dp0` or PowerShell `-Path` instead of `-LiteralPath` | quote every path; use `-LiteralPath` |
| Garbled Korean | console code page | `chcp 65001`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` (already in BATs) |
| Python not found | not 3.11–3.13 x64 / py launcher missing | `tools/bootstrap.ps1` Find-Python order; never auto-install without the Y/N prompt |
| pip fails behind proxy | SSL/proxy | report; never disable SSL verification |
| tests fail only on Windows | open file handles block TemporaryDirectory cleanup, path case, `os.open` modes, `\` vs `/` | close Pillow images (`with Image.open`), use `Path`, avoid POSIX-only assumptions |
| Task does not run | user not signed in / moved folder / time format | re-register via `enable_daily_review.bat`; check `09_LOGS/daily/` |
| `PIPELINE_BUSY` forever | stale `07_DATA/state/pipeline.lock` after a crash | doctor shows age; user deletes it after confirming no run is active — never auto-delete |

## Rules
- Fix the cause in code/BAT, add a static or unit test that would have caught it, re-run `qa-verify`.
- CI never registers a scheduled task and never publishes; keep it that way.
- Interactive prompts in BATs end with `pause`; CI calls them with `< NUL`. Unattended Python (`run_once.py`) must never call `input()`.
