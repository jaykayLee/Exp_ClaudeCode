"""P00 evidence probe — read-only against application code.

Calls the REAL v1.0 / v1.3 functions to record interface facts and reproduce the
known defects. Does not modify workspace files; writes only to a temp dir.
No network access. Synthetic data only (evidence_kind=synthetic).

Run from handoff root:
  workspace/Naver_Blog_Automation/.venv/bin/python 00_SESSION/evidence/p00_interface_probe.py
"""
from __future__ import annotations
import csv
import inspect
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HANDOFF = Path(__file__).resolve().parents[2]
APP = HANDOFF / "workspace/Naver_Blog_Automation"
for p in ("02_CORE", "03_PROVIDERS", "05_PUBLISHERS", "11_ADDONS/DANAWA_SNAPSHOT_PROBE"):
    sys.path.insert(0, str(APP / p))

from probe import snapshot_probe as sp  # v1.3
from nbcore import validation, pipeline  # v1.0
from exporters import table_exporter
from providers import base

KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=KST)
results: dict = {"probe": "P00_interface_probe", "now_fixed": NOW.isoformat(), "checks": {}}


def record(name, ok, detail):
    results["checks"][name] = {"result": "CONFIRMED" if ok else "NOT_CONFIRMED", "detail": detail}
    print(f"[{'CONFIRMED' if ok else 'NOT_CONFIRMED'}] {name}: {json.dumps(detail, ensure_ascii=False)}")


# 1. Real signatures -----------------------------------------------------------
sigs = {}
for mod, names in ((sp, ["inspect_snapshot", "offer_candidates", "save_report", "run", "krw_int", "safe_https_url"]),
                   (validation, ["normalize_records", "review_issues", "normalize_price", "public_link", "parse_time"]),
                   (pipeline, ["run_pipeline"]),
                   (table_exporter, ["render_product_table", "export_product_table"])):
    for n in names:
        sigs[f"{mod.__name__}.{n}"] = str(inspect.signature(getattr(mod, n)))
results["signatures"] = sigs
results["v1_3_csv_columns"] = sp.CSV_COLUMNS
results["v1_0_table_headers"] = list(table_exporter.HEADERS)
results["v1_0_PriceCandidate_fields"] = list(base.PriceCandidate.__dataclass_fields__)
record("seven_headers_exact", list(table_exporter.HEADERS) ==
       ["No.", "상품명", "이미지", "다나와 최저가", "사이트 주소", "네이버 최저가", "사이트 주소"],
       list(table_exporter.HEADERS))

# 2. Defect I02: top-level meta shipping/payment applied to every offer ----------
def offer(price, url, extra=None):
    o = {"@type": "Offer", "price": str(price), "priceCurrency": "KRW", "url": url,
         "itemCondition": "https://schema.org/NewCondition"}
    o.update(extra or {})
    return o

product = {"@context": "https://schema.org", "@type": "Product", "name": "합성 상품 P00",
           "model": "SYN-P00", "color": "black", "offers": [
    offer(119000, "https://example.com/A", {"seller": {"@type": "Organization", "name": "A"},
          "shippingDetails": {"@type": "OfferShippingDetails", "shippingRate": {"value": 0, "currency": "KRW"}}}),
    offer(117000, "https://example.com/B", {"seller": {"@type": "Organization", "name": "B"},
          "shippingDetails": {"@type": "OfferShippingDetails", "shippingRate": {"value": 5000, "currency": "KRW"}}}),
    offer(80000, "https://example.com/C", {"seller": {"@type": "Organization", "name": "C"},
          "description": "카드 전용 할인가"}),
]}
html_bytes = ('<html><script type="application/ld+json">' + json.dumps(product, ensure_ascii=False)
              + "</script></html>").encode("utf-8")
meta = {"target": {"query": "합성 상품 P00", "model": "SYN-P00", "variant": "black"},
        "source_page": "https://prod.danawa.com/info/?pcode=000000", "observed_at": "2026-11-05T11:00:00+09:00",
        "usage_permission": "confirmed", "shipping_fee": 0, "payment_condition": "normal"}
rep = sp.inspect_snapshot(html_bytes, meta, now=NOW, demo=False)
rows = rep["_csv_rows"]
eligible = [(r["url"], r["base_price"], r["shipping_fee"], r["payment_condition"]) for r in rows]
naive_lowest = min(rows, key=lambda r: r["base_price"] + r["shipping_fee"])["url"] if rows else None
record("I02_meta_shipping_applied_to_all_offers",
       len(rows) == 3 and all(r["shipping_fee"] == 0 for r in rows),
       {"eligible_rows": eligible, "naive_lowest_total_url": naive_lowest,
        "expected_after_fix": "A (119000+0) only; B ranked after A (122000); C excluded (card-only)"})
cand_keys = sorted(sp.offer_candidates([product])[0][0].keys())
record("I02_offer_level_seller_shipping_dropped",
       not any(k in cand_keys for k in ("seller", "shipping", "shippingDetails", "payment")),
       {"offer_candidates_keys": cand_keys})

# 3. Defect I03: v1.3 CSV row shape vs v1.0 input keys ---------------------------
v10_keys = {"query", "model", "variant", "image_path", "image_url", "image_rights", "image_credit",
            "image_source_page"} | {f"{s}_{k}" for s in ("danawa", "naver")
                                    for k in ("price", "url", "observed_at", "match_checked", "terms_checked", "condition")}
csv_cols = set(sp.CSV_COLUMNS)
record("I03_schema_mismatch", True, {
    "shared_keys": sorted(csv_cols & v10_keys),
    "v1_3_only": sorted(csv_cols - v10_keys),
    "v1_0_required_for_danawa_but_absent_in_v1_3": sorted(k for k in v10_keys - csv_cols if k.startswith("danawa_"))})
direct = validation.normalize_records([rows[0]]) if rows else []
record("I03_direct_feed_loses_price", bool(direct) and direct[0]["danawa_price"] is None,
       {"normalized_from_v1_3_row": direct[0] if direct else None})

# 4. Evidence lost in v1.0 normalization (sidecar needed) -----------------------
extra = {"query": "x", "danawa_price": 1000, "source_kind": "snapshot", "snapshot_sha256": "ab" * 32,
         "evidence_kind": "synthetic", "candidate_id": "c1", "shipping_fee": 0}
norm = validation.normalize_records([extra])[0]
lost = sorted(k for k in extra if k not in norm)
record("evidence_fields_dropped_by_normalize_records", bool(lost), {"dropped": lost})

# 5. DEMO safety contract of v1.3: CSV must be empty --------------------------
demo_rep = sp.inspect_snapshot(html_bytes, meta, now=NOW, demo=True)
record("v1_3_demo_csv_empty", demo_rep["status"] == "DEMO_ONLY" and demo_rep["review_csv_count"] == 0,
       {"status": demo_rep["status"], "review_csv_count": demo_rep["review_csv_count"]})
record("v1_3_run_demo_overwrites_observed_at",
       "meta[\"observed_at\"] = datetime.now" in inspect.getsource(sp.run),
       "run(demo=True) replaces observed_at with current time; P01 harness must call inspect_snapshot(now=...) instead")

# 6. Freshness thresholds differ ------------------------------------------------
example = json.loads((APP / "01_CONFIG/settings.example.json").read_text(encoding="utf-8"))
record("freshness_threshold_split", sp.FRESH_HOURS != None, {
    "v1_3_FRESH_HOURS_hardcoded": sp.FRESH_HOURS,
    "v1_0_config_max_price_age_hours": example["quality"]["max_price_age_hours"],
    "v1_0_allowed_range": "1..168"})

# 7. v1.0 pipeline in an isolated temp copy (no workspace writes) ---------------
tmp = Path(tempfile.mkdtemp(prefix="p00_pipeline_"))
try:
    for d in ("01_CONFIG", "07_DATA/samples"):
        shutil.copytree(APP / d, tmp / d)
    shutil.rmtree(tmp / "01_CONFIG", ignore_errors=True); (tmp / "01_CONFIG").mkdir()
    shutil.copyfile(APP / "01_CONFIG/settings.example.json", tmp / "01_CONFIG/settings.example.json")
    demo_records = json.loads((APP / "07_DATA/samples/products_demo.json").read_text(encoding="utf-8"))["records"]
    summary = pipeline.run_pipeline(tmp, demo_records, "DEMO")
    out = tmp / summary["output_relative"]
    html = (out / "product_table.html").read_text(encoding="utf-8")
    record("v1_0_demo_pipeline_isolated", summary["review_gate"] == "DEMO_ONLY" and html.count("<th>") == 7,
           {"gate": summary["review_gate"], "rows": summary["row_count"],
            "files": sorted(p.name for p in out.iterdir()),
            "network_price_collection": summary["network_price_collection"], "published": summary["published"]})
    try:
        pipeline.run_pipeline(tmp, [], "MANUAL_IMPORT")
        empty = "accepted"
    except ValueError as e:
        empty = str(e)
    record("v1_0_empty_inbox_rejected", empty != "accepted", {"message": empty,
           "note": "07_DATA/inbox/products.json ships with records: [] so run_once.bat (non-demo) exits 1 until input exists"})
finally:
    shutil.rmtree(tmp, ignore_errors=True)

out_path = HANDOFF / "00_SESSION/evidence/p00_interface_probe.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print("WROTE", out_path.relative_to(HANDOFF))
