#!/usr/bin/env bash
# Prepare the Linux dev environment for a cloud session. Idempotent.
# Never runs BAT files, never registers schedules, never posts anywhere.
# Run manually at session start:  bash scripts/cloud_session_setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$ROOT/workspace/Naver_Blog_Automation"
cd "$APP"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -q --disable-pip-version-check --only-binary=:all: -r tools/dependencies.lock
# Dev-only QA helpers (not shipped, not in the lock): browser UI QA and YAML checks.
.venv/bin/python -m pip install -q --disable-pip-version-check playwright pyyaml >/dev/null 2>&1 || echo "[setup] optional dev tools not installed (offline?)"
echo "[setup] venv ready: $APP/.venv  | next: read 00_SESSION/PHASE_HANDOFF.md"
