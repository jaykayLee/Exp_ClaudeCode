"""Build the end-user install ZIP (P06). Local file operation only; nothing is uploaded or published.

User data, secrets, caches, run outputs and the virtual environment are never packed.
07_DATA/inbox/products.json is written as an empty default instead of copying the user's file.

  .venv/bin/python tools/build_release.py --out ../dist
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from environment import ROOT
from nbcore.validation import now_kst

PACKAGE = "Naver_Blog_Automation"
SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", ".pytest_cache"}
SKIP_FILES = ["*.pyc", "*.tmp", ".write_test", "*.env", "credentials*.json", "token*.json", "*.log",
              "01_CONFIG/settings.local.json", "07_DATA/state/pipeline.lock",
              "00_PROJECT/RELEASE_MANIFEST.json"]   # regenerated per build (rebuild from an installed copy)
# Folders whose contents are user/runtime data: only the listed files are kept.
DATA_DIRS = {
    "07_DATA/inbox": set(),                     # products.json is generated empty below
    "07_DATA/images": {"original/README.md"},
    "07_DATA/state": {"README.md"},
    "08_OUTPUT": set(),
    "09_LOGS": {"README.md"},
    "04_CONTENT/briefs": set(),
    "11_ADDONS/DANAWA_SNAPSHOT_PROBE/output": {".gitkeep"},
}
GENERATED = {"07_DATA/inbox/products.json": json.dumps({"records": []}, indent=2) + "\n"}
REQUIRED = ["install.bat", "start_panel.bat", "doctor.bat", "smoke.bat", "run_once.bat", "run_snapshot.bat",
            "run_snapshot_demo.bat", "enable_daily_review.bat", "disable_daily_review.bat", "open_guide.bat",
            "tools/bootstrap.ps1", "tools/dependencies.lock", "tools/server.py", "tools/run_once.py",
            "tools/run_snapshot_to_panel.py", "06_UI/index.html", "01_CONFIG/settings.example.json",
            "07_DATA/samples/snapshot_demo/job.json", "11_ADDONS/DANAWA_SNAPSHOT_PROBE/probe/snapshot_probe.py",
            "00_PROJECT/QA/WINDOWS_ACCEPTANCE.md"]
SECRET = re.compile(rb"(?i)(password|passwd|api[_-]?key|secret|access[_-]?token|cookie)\s*[\"']?\s*[:=]\s*[\"'][^\"'\s]{12,}")


def include(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in SKIP_DIRS for p in parts):
        return False
    if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(parts[-1], pat) for pat in SKIP_FILES):
        return False
    for folder, keep in DATA_DIRS.items():
        if rel.startswith(folder + "/"):
            return rel[len(folder) + 1:] in keep
    return True


def collect(root: Path) -> dict[str, bytes]:
    files = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not path.is_symlink() and include(rel):
            files[rel] = path.read_bytes()
    for rel, text in GENERATED.items():
        files[rel] = text.encode("utf-8")
    return files


def build(root: Path, out_dir: Path, label: str) -> dict:
    root, out_dir = Path(root).resolve(), Path(out_dir).resolve()
    if out_dir.is_relative_to(root):
        raise ValueError("OUTPUT_INSIDE_WORKSPACE: choose a folder outside the workspace")
    files = collect(root)
    missing = [r for r in REQUIRED if r not in files]
    if missing:
        raise ValueError("REQUIRED_FILES_MISSING: " + ", ".join(missing))
    leaks = [r for r, data in files.items() if SECRET.search(data)]
    if leaks:
        raise ValueError("SECRET_LIKE_VALUE_FOUND: " + ", ".join(leaks))
    manifest = {"package": PACKAGE, "label": label, "built_at": now_kst().isoformat(),
                "note": "설치형 배포본. 사용자 입력·설정·이미지·실행 결과·로그·가상환경은 포함하지 않음.",
                "verified_here": "Linux build/re-extract only. Windows execution: NEEDS_WINDOWS_CHECK.",
                "files": [{"path": r, "sha256": hashlib.sha256(d).hexdigest(), "bytes": len(d)} for r, d in files.items()]}
    files["00_PROJECT/RELEASE_MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{PACKAGE}_{label}.zip"
    temp = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            info = zipfile.ZipInfo(f"{PACKAGE}/{rel}", date_time=(2026, 11, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, files[rel])
    temp.replace(target)
    with zipfile.ZipFile(target) as z:
        if z.testzip():
            raise ValueError("ZIP_CRC_FAILED")
        count = len(z.namelist())
    return {"zip": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "files": count, "bytes": target.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the install ZIP (local only).")
    parser.add_argument("--out", type=Path, required=True, help="output folder outside the workspace")
    parser.add_argument("--label", default=now_kst().strftime("%Y%m%d"), help="file name label")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", args.label):
        print("[ERROR] label: letters, digits, . _ - only", file=sys.stderr)
        return 1
    try:
        print(json.dumps(build(ROOT, args.out, args.label), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print("[ERROR] " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
