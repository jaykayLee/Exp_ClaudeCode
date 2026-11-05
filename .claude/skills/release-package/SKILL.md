---
name: release-package
description: Package and deliver phase results for the Naver Blog automation project — release manifest, handoff ZIP, Windows install ZIP, full-history git bundle, resume MD, re-extract verification, and delivery with download links on the last line. Use when a phase ends or the user asks for "ZIP", "결과물", "다운로드", "백업".
---

# Release package

## Steps
1. Commit everything (`git status` clean except ignored files).
2. Manifest: write `RELEASE_MANIFEST_<PHASE>.json` at repo root listing every `git ls-files` entry (sha256, bytes) + `preserved_originals` for `reference/originals/*.zip`. Name must sort after older manifests (`tools/verify_release.py` uses the latest by name). Run `python3 tools/verify_release.py` → PASS, then commit.
3. Install ZIP: `cd workspace/Naver_Blog_Automation && .venv/bin/python tools/build_release.py --out /home/user/<PHASE>_다운로드 --label <PHASE>_<YYYYMMDD>` (refuses output inside the workspace; excludes user data/secrets).
4. Handoff ZIP: `git archive HEAD` into a staging dir named `Naver_Blog_Cloud_Handoff_v1.0/`, zip it as `Naver_Blog_Cloud_Handoff_v1.0_<PHASE>.zip`.
5. Bundle: `git bundle create <dir>/naver_blog_automation_full_history.bundle HEAD main` (HEAD is required or the clone has no branch).
6. Re-extract checks (temp dir, never the repo): unzip handoff → `verify_release.py` PASS; clone bundle → commit count + `verify_release.py` PASS; unzip install ZIP into a path with space+Korean → venv/lock/doctor/qa_runner.
7. Resume MD `Naver_Blog_<PHASE>_Resume.md`: sha256 of each ZIP/bundle, status per phase, checks run, not-run list, user commands, next single phase + required input.

## Delivery (user requirement)
- Put deliverables in a folder directly under the primary working directory (e.g. `/home/user/<PHASE>_다운로드/`), not deep in the repo — files outside the app-visible area do not show up.
- Call SendUserFile with all files (`display: attach` for ZIP/bundle/MD).
- The LAST line of the final answer is always: `📥 받을 파일: [name](absolute path) · ...` for every deliverable.

## Never
Include `.venv`, `__pycache__`, `01_CONFIG/settings.local.json`, `07_DATA/inbox` user files, `08_OUTPUT/runs`, `09_LOGS` runtime files, secrets. Never `rm -rf` with an unguarded shell variable — use literal paths or `"${VAR:?}"`.
