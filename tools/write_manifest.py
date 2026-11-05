"""Regenerate the release manifest for the current git state. Run it LAST, right before the final commit.

  python3 tools/write_manifest.py P07 "short note"
Writes RELEASE_MANIFEST_<label>.json listing every tracked (or staged) file except the manifest itself,
plus hashes of reference/originals/*.zip. tools/verify_release.py checks the latest manifest by name.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2 or not re.fullmatch(r"P\d{2}[A-Za-z0-9_]*", sys.argv[1]):
        print("usage: write_manifest.py P07 [note]", file=sys.stderr)
        return 2
    label, note = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    name = f"RELEASE_MANIFEST_{label}.json"
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    files = [f for f in subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
             if f != name]
    latest = sorted(p.name for p in ROOT.glob("RELEASE_MANIFEST_*.json") if p.name != name)
    if latest and latest[-1] > name:
        print(f"[ERROR] {name} would not be the latest manifest (found {latest[-1]})", file=sys.stderr)
        return 1
    manifest = {
        "phase": label, "date": datetime.now(timezone(timedelta(hours=9))).date().isoformat(), "note": note,
        "previous_release": latest[-1] if latest else None,
        "preserved_originals": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / "reference/originals").glob("*.zip"))},
        "files": [{"path": f, "sha256": hashlib.sha256((ROOT / f).read_bytes()).hexdigest(), "bytes": (ROOT / f).stat().st_size}
                  for f in files if (ROOT / f).is_file()],
    }
    (ROOT / name).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: {len(manifest['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
