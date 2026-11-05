# Repository entry point

## Start of every session (cloud or local)
1. `bash scripts/cloud_session_setup.sh` (creates `workspace/Naver_Blog_Automation/.venv`, installs the lock).
2. Read `00_SESSION/PHASE_HANDOFF.md`, `00_SESSION/PHASE_STATUS.json`, `00_SESSION/OPEN_ISSUES.md`.
3. Read `MASTER_IMPLEMENTATION_PROMPT_KO.md` only for rules; do not re-analyse original ZIPs.

## Rules
- One phase per session/PR; save checkpoints (git commit) after each passing step; STOP at phase end.
- Work in `workspace/Naver_Blog_Automation`. Preserve `reference/originals` (hash-checked).
- v1.1/v1.2 originals are not included. Do not invent compatibility or tests.
- Linux tests, real-site tests and Windows tests are distinct. CI `windows` job runs real BAT files on a GitHub runner — that is Windows evidence for a clean runner, not for the user's PC.
- External publication, paid calls, public deployment, live scraping and schedule registration are OFF unless separately authorized.
- `.gitattributes` is `* -text`: never convert line endings (BAT/PS1 stay CRLF; manifests hash exact bytes).

## Verify
- `cd workspace/Naver_Blog_Automation && .venv/bin/python tools/qa_runner.py`
- `python3 tools/verify_release.py` (latest RELEASE_MANIFEST_*.json)
- Push → GitHub Actions `ci` (linux + windows).
