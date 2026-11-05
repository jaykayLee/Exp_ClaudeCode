"""Verify a phase release against RELEASE_MANIFEST_*.json (latest by name).

The pristine ARTIFACT_MANIFEST.json + verify_handoff.py describe the original handoff
only; after a phase, use this script. No network, no installation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifests = sorted(ROOT.glob("RELEASE_MANIFEST_*.json"))
    if not manifests:
        print("ERROR: no RELEASE_MANIFEST_*.json", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
        failures = []
        for item in manifest["files"]:
            p = ROOT / item["path"]
            if not p.is_file():
                failures.append("MISSING: " + item["path"])
            elif hashlib.sha256(p.read_bytes()).hexdigest() != item["sha256"]:
                failures.append("HASH_MISMATCH: " + item["path"])
        for name, digest in manifest["preserved_originals"].items():
            p = ROOT / name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                failures.append("ORIGINAL_CHANGED: " + name)
            else:
                with ZipFile(p) as z:
                    if z.testzip():
                        failures.append("ZIP_CRC: " + name)
        print(f"{manifests[-1].name}: phase={manifest['phase']} files={len(manifest['files'])}")
        if failures:
            print("\n".join(failures))
            return 1
        print("PASS: release file hashes and preserved original ZIPs.")
        print("NOT a claim of Windows, live scraping, E2E or blog publication success.")
        return 0
    except (OSError, ValueError, KeyError, BadZipFile) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
