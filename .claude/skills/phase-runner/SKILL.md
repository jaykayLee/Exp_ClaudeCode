---
name: phase-runner
description: Run exactly one project phase (P07, P08, ...) of the Naver Blog price-table automation end to end — session setup, read status, fix acceptance criteria, implement with checkpoint commits, update 00_SESSION files, package, and report in the required format. Use when the user says "P0x 수행", "다음 Phase 진행", "이어서 작업", or uploads a handoff ZIP/resume MD.
---

# Phase runner

One session (or PR) = one phase. Never start the next phase automatically.

## 1. Start (≤ 5 tool calls)
1. `bash scripts/cloud_session_setup.sh` (venv + lock; idempotent).
2. If the user uploaded a ZIP/bundle: verify its sha256 against the resume MD, then continue in the existing git checkout if hashes match; otherwise `git clone <bundle>`.
3. Read only: `00_SESSION/PHASE_HANDOFF.md`, `00_SESSION/PHASE_STATUS.json`, `00_SESSION/OPEN_ISSUES.md`, the phase entry in `docs/BACKLOG_P07_P10.md`.
4. Baseline: `cd workspace/Naver_Blog_Automation && .venv/bin/python tools/qa_runner.py` — record the count before changing anything.
5. Write the phase's acceptance criteria (numbered) in your first message before editing code.

## 2. Implement
- Prefer adapters/new modules over editing v1.0 core (`02_CORE/nbcore/*`, `02_CORE/exporters/table_exporter.py`, `03_PROVIDERS/providers/base.py`). If core must change, add a migration + regression test and record it in `00_SESSION/DECISIONS.md`.
- After each passing step: `git add -A && git commit` (message ends with the attribution lines from the system reminder). Never push unless the user asked.
- Same failure twice with the same approach → change approach or record a blocker; do not loop.
- Follow the `price-data-contract` skill for anything touching prices, URLs, timestamps or the 7-column table.

## 3. Finish
1. Run the `qa-verify` skill (all checks, honest counts).
2. Update `00_SESSION/PHASE_STATUS.json`, `PHASE_HANDOFF.md`, `OPEN_ISSUES.md`, `TEST_RESULTS.json`, append `DECISIONS.md`.
3. Run the `release-package` skill (handoff ZIP + resume MD + bundle, download links on the last line).
4. Final answer contract (Korean): ① 구현한 것 ② 실제 실행한 검사·결과·환경 ③ 미구현/미검증/blocked ④ 사용자가 실행할 BAT·명령 ⑤ 다음 단일 Phase와 필요한 입력 — then the 📥 download line as the LAST line.

## Status words
`NOT_STARTED / IN_PROGRESS / PASS / FAIL / BLOCKED_INPUT / BLOCKED_EXTERNAL / NEEDS_WINDOWS_CHECK / NOT_RUN`. Implementation status and real-site/Windows verification are separate fields. A Linux pass is never a Windows pass; a synthetic pass is never a live pass.
