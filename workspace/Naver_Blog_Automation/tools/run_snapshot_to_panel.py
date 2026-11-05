"""Single entry point (P01): saved Danawa snapshot(s) -> per-offer checks -> v1.0 pipeline -> 7-column table.

Local review only. No network, no login, no publication. Uses the existing v1.0
run_pipeline() unchanged and stores the evidence that v1.0 normalization drops
in <run>/bridge/evidence_sidecar.json.

Job file (JSON, paths relative to the job file, all inside the workspace):
{
  "schema_version": "snapshot_job.1",
  "mode": "DEMO" | "MANUAL_IMPORT",
  "evidence_kind": "synthetic" (DEMO only) | "user_recorded" (MANUAL_IMPORT only),
  "evaluation_time": "<ISO8601+tz>"  (optional, DEMO only; fixed clock for synthetic fixtures),
  "products": [{"query": "...", "html": "a.html", "meta": "a_meta.json",
                "image_path": "07_DATA/...", "image_rights": "owned", "image_credit": "..."}]
}
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from environment import ROOT

sys.path.insert(0, str(ROOT / "11_ADDONS/DANAWA_SNAPSHOT_PROBE"))

from nbcore.config import load_config  # noqa: E402
from nbcore.pipeline import atomic_json, run_pipeline  # noqa: E402
from nbcore.validation import now_kst, parse_time  # noqa: E402
from probe import snapshot_probe  # noqa: E402
from providers import snapshot_adapter as adapter  # noqa: E402

JOB_SCHEMA = "snapshot_job.1"
MAX_JOB_BYTES = 1024 * 1024
MAX_META_BYTES = 256 * 1024
MAX_PRODUCTS = 30
DEMO_JOB = "07_DATA/samples/snapshot_demo/job.json"


def _inside(root: Path, base: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"{field.upper()}_PATH_REQUIRED")
    path = (base / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"PATH_OUTSIDE_WORKSPACE: {field}")
    return path


def _read_json(path: Path, limit: int, code: str) -> object:
    if not path.is_file():
        raise ValueError(f"{code}_NOT_FOUND: {path.name}")
    if path.stat().st_size > limit:
        raise ValueError(f"{code}_TOO_LARGE")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jobs(input_paths: list[Path], root: Path) -> tuple[str, str, str | None, list[dict]]:
    if not input_paths:
        raise ValueError("JOB_REQUIRED")
    modes, kinds, clocks, products = set(), set(), set(), []
    for raw in input_paths:
        job_path = _inside(root, Path.cwd(), str(raw), "job")
        job = _read_json(job_path, MAX_JOB_BYTES, "JOB")
        if not isinstance(job, dict) or job.get("schema_version") != JOB_SCHEMA:
            raise ValueError(f"JOB_SCHEMA_INVALID: expected {JOB_SCHEMA}")
        if not isinstance(job.get("products"), list) or not job["products"]:
            raise ValueError("JOB_PRODUCTS_REQUIRED")
        modes.add(job.get("mode"))
        kinds.add(job.get("evidence_kind"))
        clocks.add(job.get("evaluation_time"))
        for item in job["products"]:
            if not isinstance(item, dict):
                raise ValueError("JOB_PRODUCT_NOT_OBJECT")
            products.append({**item, "_base": job_path.parent})
    if len(modes) != 1 or len(kinds) != 1 or len(clocks) != 1:
        raise ValueError("JOBS_MUST_SHARE_MODE_EVIDENCE_KIND_AND_CLOCK")
    if not 1 <= len(products) <= MAX_PRODUCTS:
        raise ValueError(f"PRODUCT_COUNT_1_TO_{MAX_PRODUCTS}")
    mode, kind, clock = modes.pop(), kinds.pop(), clocks.pop()
    adapter.check_evidence_kind(kind, mode)
    return mode, kind, clock, products


def _evaluation_clock(mode: str, declared: object, now: datetime | None) -> tuple[datetime, str]:
    if declared is not None:
        if mode != "DEMO":
            raise ValueError("EVALUATION_TIME_ONLY_FOR_DEMO")
        stamp = parse_time(declared)
        if stamp is None:
            raise ValueError("EVALUATION_TIME_INVALID")
        return stamp, "job_demo_fixed_clock"
    if now is not None:
        if now.tzinfo is None:
            raise ValueError("NOW_REQUIRES_TIMEZONE")
        return now, "caller"
    return now_kst(), "system_clock"


def _process_product(root: Path, item: dict, *, mode: str, kind: str, clock: datetime,
                     max_age: int, processed_at: str) -> dict:
    query = str(item.get("query") or "").strip()[:200] or "미입력 상품"
    target = {"query": query, "model": str(item.get("model") or ""), "variant": str(item.get("variant") or "")}
    for key in ("image_path", "image_url", "image_rights", "image_credit", "image_source_page"):
        if isinstance(item.get(key), str):
            target[key] = item[key]
    entry = {"query": query, "html_file": None, "meta_file": None, "snapshot_sha256": None,
             "probe_version": snapshot_probe.VERSION, "probe_status": None, "probe_review_csv_count": None,
             "status": None, "error": None, "warnings": [], "candidates": [], "selection": None, "_report": None}
    try:
        base = item["_base"]
        html_path = _inside(root, base, item.get("html"), "html")
        meta_path = _inside(root, base, item.get("meta"), "meta")
        entry["html_file"] = html_path.relative_to(root.resolve()).as_posix()
        entry["meta_file"] = meta_path.relative_to(root.resolve()).as_posix()
        if not html_path.is_file():
            raise ValueError("HTML_NOT_FOUND")
        if html_path.stat().st_size > snapshot_probe.MAX_HTML_BYTES:
            raise ValueError("HTML_TOO_LARGE")
        meta = _read_json(meta_path, MAX_META_BYTES, "META")
        if not isinstance(meta, dict):
            raise ValueError("META_NOT_OBJECT")
        meta_target = meta.get("target") if isinstance(meta.get("target"), dict) else {}
        for key in ("query", "model", "variant"):
            declared = str(meta_target.get(key) or "").strip()
            if declared and target[key] and declared != target[key].strip():
                raise ValueError(f"TARGET_{key.upper()}_MISMATCH_JOB_VS_META")
            target[key] = target[key] or declared
        report = snapshot_probe.inspect_snapshot(html_path.read_bytes(), meta, now=clock,
                                                 demo=(mode == "DEMO"), fresh_hours=max_age)
        entry.update(snapshot_sha256=report["snapshot_sha256"], probe_status=report["status"],
                     probe_review_csv_count=report["review_csv_count"], warnings=report["warnings"],
                     _report=report)
        candidates = adapter.normalize_snapshot_candidates(
            report, meta.get("offer_terms"), evidence_kind=kind, collected_at=processed_at, meta=meta)
        evaluated = adapter.evaluate_candidates(target, candidates, now=clock, max_age_hours=max_age,
                                                demo=(mode == "DEMO"))
        selection = adapter.select_lowest_eligible(evaluated)
        if not evaluated:
            selection["excluded"] = [{"candidate_id": None, "url": None,
                                      "reasons": report["warnings"] or ["NO_STRUCTURED_OFFERS"]}]
        entry.update(candidates=evaluated, status=selection["status"])
    except (OSError, UnicodeError, ValueError, KeyError) as exc:  # json.JSONDecodeError is a ValueError
        selection = {"status": "SNAPSHOT_FAILED", "selected": None, "ranking": [], "ties": [],
                     "excluded": [{"candidate_id": None, "url": None, "reasons": [f"SNAPSHOT_FAILED:{exc}"[:160]]}],
                     "basis": adapter.PRICE_BASIS, "basis_code": adapter.PRICE_BASIS_CODE}
        entry.update(status="SNAPSHOT_FAILED", error=f"{type(exc).__name__}: {exc}"[:300])
    entry["panel_record"] = adapter.to_panel_input(target, selection, evidence_kind=kind)
    chosen = selection.get("selected")
    entry["selection"] = {k: v for k, v in selection.items() if k != "selected"}
    entry["selection"]["selected_candidate_id"] = chosen["candidate_id"] if chosen else None
    return entry


def run_snapshot_to_panel(input_paths: list[Path], root: Path = ROOT, *, now: datetime | None = None) -> dict:
    """Process jobs, run the unchanged v1.0 pipeline, then store bridge evidence next to its output."""
    root = Path(root)
    config = load_config(root)
    max_age = config["quality"]["max_price_age_hours"]
    mode, kind, declared_clock, products = load_jobs(input_paths, root)
    clock, clock_source = _evaluation_clock(mode, declared_clock, now)
    processed_at = now_kst().isoformat()
    entries = [_process_product(root, item, mode=mode, kind=kind, clock=clock, max_age=max_age,
                                processed_at=processed_at) for item in products]
    summary = run_pipeline(root, [e["panel_record"] for e in entries], mode)
    bridge = root / summary["output_relative"] / "bridge"
    bridge.mkdir(parents=True, exist_ok=True)
    for i, entry in enumerate(entries, 1):
        report = entry.pop("_report")
        if report is not None:
            snapshot_probe.save_report(report, bridge / f"product_{i:02d}_probe")
    sidecar = {
        "sidecar_version": "1",
        "adapter": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
        "compatibility": adapter.LEGACY_FLAG,
        "note": "신규 직접 어댑터. 누락된 v1.1/v1.2 Add-on의 재현·호환 구현이 아님.",
        "mode": mode, "evidence_kind": kind, "review_gate": summary["review_gate"],
        "pipeline_run_id": summary["run_id"], "processed_at": processed_at,
        "evaluation_time": clock.isoformat(), "evaluation_time_source": clock_source,
        "max_price_age_hours": max_age, "price_basis": adapter.PRICE_BASIS,
        "result_scope": "확인한 적합 후보 내 최저가 (전체 시장·사이트 절대 최저가 아님)",
        "sources": {"danawa": "saved_html_snapshot", "naver": "NOT_CONNECTED"},
        "network_requests": False, "published": False,
        "products": [{"row": i, **e} for i, e in enumerate(entries, 1)],
    }
    atomic_json(bridge / "evidence_sidecar.json", sidecar)
    return {"run_id": summary["run_id"], "mode": mode, "evidence_kind": kind,
            "review_gate": summary["review_gate"], "reused_output": summary["reused_output"],
            "output_relative": summary["output_relative"],
            "sidecar": (bridge / "evidence_sidecar.json").relative_to(root).as_posix(),
            "published": False,
            "products": [{"row": i, "query": e["query"], "status": e["status"],
                          "danawa_price": e["panel_record"]["danawa_price"],
                          "danawa_url": e["panel_record"]["danawa_url"]} for i, e in enumerate(entries, 1)]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Saved-snapshot to 7-column review table. Never posts.")
    parser.add_argument("--job", action="append", type=Path, default=[], help="snapshot job JSON (repeatable)")
    parser.add_argument("--demo", action="store_true", help=f"use synthetic {DEMO_JOB}")
    args = parser.parse_args()
    jobs = [ROOT / DEMO_JOB] if args.demo else args.job
    try:
        result = run_snapshot_to_panel(jobs, ROOT)
    except (ValueError, OSError) as exc:
        print("[ERROR] " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
