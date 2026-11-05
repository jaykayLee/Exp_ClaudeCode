"""Daily / one-off local review run. Never collects live prices, logs in, or posts to a blog.

Default (used by run_once.bat and the optional Windows scheduled task):
  - 07_DATA/inbox/snapshot_job.json  -> saved-snapshot bridge (if the file exists)
  - 07_DATA/inbox/products.json      -> v1.0 manual-input pipeline (if it has records)
Each input is processed independently: one failure does not hide the other's result.
Every run writes 09_LOGS/daily/run_<timestamp>.json because scheduled runs have no console.

Exit codes: 0 = all attempted inputs processed (HOLD/DEMO_ONLY are normal review results)
            or nothing to process (NO_INPUT); 1 = at least one input failed (see the log).
Never prompts for input, so it is safe for unattended runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from environment import ROOT
from nbcore.pipeline import atomic_json, run_pipeline
from nbcore.validation import now_kst
from exporters.naver_paste import write_for_run

PRODUCTS = "07_DATA/inbox/products.json"
SNAPSHOT_JOB = "07_DATA/inbox/snapshot_job.json"
DEMO_PRODUCTS = "07_DATA/samples/products_demo.json"
LOCK = "07_DATA/state/pipeline.lock"
MAX_INPUT_BYTES = 2 * 1024 * 1024


def lock_info(root: Path) -> dict | None:
    """Describe an existing pipeline lock. It is never deleted automatically."""
    path = root / LOCK
    if not path.exists():
        return None
    info: dict = {"path": LOCK}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        info.update(pid=data.get("pid"), started_at=data.get("started_at"))
        started = datetime.fromisoformat(str(data.get("started_at")))
        info["age_minutes"] = round((now_kst() - started).total_seconds() / 60, 1)
    except (OSError, ValueError, TypeError) as exc:
        info["unreadable"] = type(exc).__name__
    return info


def _products(root: Path, path: Path, mode: str) -> dict:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("INPUT_TOO_LARGE: max 2 MiB")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("INPUT_OBJECT_REQUIRED: use {records: [...]} JSON")
    records = payload.get("records", [])
    if mode == "MANUAL_IMPORT" and records == []:
        return {"status": "NO_INPUT", "detail": "records 목록이 비어 있습니다."}
    summary = run_pipeline(root, records, mode)
    write_for_run(root, summary)
    return {"status": "DONE", "review_gate": summary["review_gate"], "run_id": summary["run_id"],
            "rows": summary["row_count"], "reused_output": summary["reused_output"],
            "output": summary["output_relative"], "published": False}


def _snapshot(root: Path, job: Path) -> dict:
    import run_snapshot_to_panel as bridge  # imported lazily: optional add-on path
    result = bridge.run_snapshot_to_panel([job], root)
    return {"status": "DONE", "review_gate": result["review_gate"], "run_id": result["run_id"],
            "rows": len(result["products"]), "reused_output": result["reused_output"],
            "output": result["output_relative"], "sidecar": result["sidecar"], "published": False,
            "products": [{"query": p["query"], "status": p["status"]} for p in result["products"]]}


def run_daily(root: Path, *, demo: bool = False, snapshot_demo: bool = False) -> tuple[int, dict]:
    started = now_kst()
    tasks: list[tuple[str, object]] = []
    if demo:
        tasks.append(("products_demo", root / DEMO_PRODUCTS))
    elif snapshot_demo:
        import run_snapshot_to_panel as bridge
        tasks.append(("snapshot_demo", root / bridge.DEMO_JOB))
    else:
        if (root / SNAPSHOT_JOB).is_file():
            tasks.append(("snapshot_job", root / SNAPSHOT_JOB))
        if (root / PRODUCTS).is_file():
            tasks.append(("products", root / PRODUCTS))
    results = {}
    for name, path in tasks:
        try:
            if name.startswith("snapshot"):
                results[name] = _snapshot(root, path)
            else:
                results[name] = _products(root, path, "DEMO" if name == "products_demo" else "MANUAL_IMPORT")
        except (ValueError, OSError) as exc:  # json.JSONDecodeError is a ValueError
            entry = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"[:400]}
            if "PIPELINE_BUSY" in str(exc):
                entry["lock"] = lock_info(root)
            results[name] = entry
    if not any(r.get("status") == "DONE" or r.get("status") == "FAILED" for r in results.values()):
        overall = "NO_INPUT"
    elif any(r.get("status") == "FAILED" for r in results.values()):
        overall = "FAILED"
    else:
        overall = "DONE"
    report = {"tool": "run_once", "started_at": started.isoformat(), "finished_at": now_kst().isoformat(),
              "overall": overall, "inputs": results,
              "notice": "로컬 검토 자료 생성만 수행. 실시간 가격 수집·로그인·블로그 게시 없음.",
              "network_price_collection": False, "published": False}
    if overall == "NO_INPUT":
        report["hint"] = (f"처리할 입력이 없습니다. {PRODUCTS}에 records를 넣거나 "
                          f"{SNAPSHOT_JOB} 작업 파일을 만드세요.")
    log_dir = root / "09_LOGS/daily"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"run_{started.strftime('%Y%m%d_%H%M%S_%f')}.json"
    atomic_json(log, report)
    report["log"] = log.relative_to(root).as_posix()
    return (1 if overall == "FAILED" else 0), report


def main() -> int:
    parser = argparse.ArgumentParser(description="Local review only; never posts to a blog.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo", action="store_true", help="v1.0 synthetic 3-product demo")
    group.add_argument("--snapshot-demo", action="store_true", help="synthetic saved-snapshot demo")
    args = parser.parse_args()
    code, report = run_daily(ROOT, demo=args.demo, snapshot_demo=args.snapshot_demo)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["overall"] == "NO_INPUT":
        print("[INFO] " + report["hint"])
    elif code:
        print("[ERROR] 일부 입력 처리 실패. 로그: " + report["log"], file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
