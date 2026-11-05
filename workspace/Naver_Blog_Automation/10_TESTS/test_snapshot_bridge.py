"""P01 acceptance tests: snapshot probe v1.3.1 -> direct adapter -> v1.0 pipeline -> 7-column table.

All data is synthetic. Live Danawa/Naver, Windows and publication are NOT tested here.
Acceptance ids refer to docs/P00_INTERFACE_MAP.md section 3 (1~8).
"""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

from environment import ROOT
import run_snapshot_to_panel as bridge  # tools/ (inserts the probe add-on path)
from probe import snapshot_probe as sp
from providers import snapshot_adapter as ad
from nbcore.validation import normalize_records

KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=KST)
OBS = "2026-11-05T11:00:00+09:00"
TARGET = {"query": "합성 상품", "model": "SYN-1", "variant": "black"}


def offer(price, url, seller, shipping=None, **extra):
    o = {"@type": "Offer", "price": price if isinstance(price, (bool, int)) else str(price),
         "priceCurrency": "KRW", "url": url, "itemCondition": "https://schema.org/NewCondition",
         "seller": {"@type": "Organization", "name": seller}}
    if shipping is not None:
        o["shippingDetails"] = {"@type": "OfferShippingDetails", "shippingRate": {"value": shipping, "currency": "KRW"}}
    o.update(extra)
    return o


def html(*offers, model="SYN-1", color="black", name="합성 상품"):
    p = {"@context": "https://schema.org", "@type": "Product", "name": name, "model": model,
         "color": color, "offers": list(offers)}
    return ('<script type="application/ld+json">' + json.dumps(p, ensure_ascii=False) + "</script>").encode()


def meta(**over):
    m = {"target": dict(TARGET), "source_page": "https://prod.danawa.com/info/?pcode=777",
         "observed_at": OBS, "usage_permission": "confirmed"}
    m.update(over)
    return m


def terms(*pairs):
    return [{"url": u, "payment_condition": p, "evidence": "합성 기록"} for u, p in pairs]


ABC_HTML = html(offer(119000, "https://example.com/A", "A", 0),
                offer(117000, "https://example.com/B", "B", 5000),
                offer(80000, "https://example.com/C", "C", description="카드 전용 할인가"))
ABC_TERMS = terms(("https://example.com/A", "normal"), ("https://example.com/B", "normal"),
                  ("https://example.com/C", "card_only"))


def pick(html_bytes, m, *, kind="user_recorded", demo=False, now=NOW, max_age=24):
    report = sp.inspect_snapshot(html_bytes, m, now=now, demo=demo, fresh_hours=max_age)
    cands = ad.normalize_snapshot_candidates(report, m.get("offer_terms"), evidence_kind=kind,
                                            collected_at=now.isoformat(), meta=m)
    evaluated = ad.evaluate_candidates(m["target"], cands, now=now, max_age_hours=max_age, demo=demo)
    return report, evaluated, ad.select_lowest_eligible(evaluated)


class Cells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headers, self.rows, self._row, self._cell, self._in = [], [], None, None, None
    def handle_starttag(self, tag, attrs):
        if tag in ("th", "td"):
            self._in, self._cell = tag, []
        elif tag == "tr":
            self._row = []
        elif tag == "a" and self._cell is not None:
            self._cell.append("HREF=" + dict(attrs).get("href", ""))
        elif tag == "img" and self._cell is not None:
            self._cell.append("IMG")
    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("th", "td") and self._cell is not None:
            text = " ".join(x.strip() for x in self._cell if x.strip())
            (self.headers if tag == "th" else self._row).append(text)
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


class AdapterSelection(unittest.TestCase):
    """Acceptance 2, 3, 4 — per-offer evaluation and selection."""

    def test_abc_selects_a_ranks_b_excludes_c(self):
        _, ev, sel = pick(ABC_HTML, meta(offer_terms=ABC_TERMS))
        self.assertEqual(sel["status"], "SELECTED")
        a = sel["selected"]
        self.assertEqual((a["seller_name"], a["base_price"], a["shipping_fee"], a["total_price"]), ("A", 119000, 0, 119000))
        self.assertEqual([r["total_price"] for r in sel["ranking"]], [119000, 122000])
        c = [x for x in ev if x["seller_name"] == "C"][0]
        self.assertFalse(c["eligible"])
        self.assertIn("PAYMENT_NOT_CONFIRMED_NORMAL", c["exclusion_reasons"])
        self.assertIn("PAYMENT_CONDITIONAL_HINT", c["exclusion_reasons"])

    def test_old_behavior_would_have_chosen_card_only(self):
        """Documents I02: legacy meta-wide terms (no scope) are no longer promoted."""
        _, ev, sel = pick(ABC_HTML, meta(shipping_fee=0, payment_condition="normal"))
        self.assertEqual(sel["status"], "NO_ELIGIBLE_CANDIDATE")
        for c in ev:
            self.assertIn("PAYMENT_NOT_CONFIRMED_NORMAL", c["exclusion_reasons"])
        # Explicit scope is still an allowed, recorded choice — and the hint still blocks C.
        _, ev2, sel2 = pick(ABC_HTML, meta(shipping_fee=0, payment_condition="normal", offer_terms_scope="all_offers"))
        self.assertEqual(sel2["selected"]["seller_name"], "A")  # A 119000+0 (JSON-LD) beats B 117000+5000
        self.assertFalse([x for x in ev2 if x["seller_name"] == "C"][0]["eligible"])

    def test_price_url_time_belong_to_same_offer(self):
        _, ev, sel = pick(ABC_HTML, meta(offer_terms=ABC_TERMS))
        a = sel["selected"]
        self.assertEqual(a["url"], "https://example.com/A")
        self.assertEqual(a["observed_at"], OBS)
        self.assertEqual(a["shipping_source"], "offer_jsonld")
        self.assertEqual(a["payment_source"], "meta_offer_terms")
        self.assertEqual(a["terms_evidence"], ["합성 기록"])
        b = [x for x in ev if x["seller_name"] == "B"][0]
        self.assertEqual((b["url"], b["base_price"], b["shipping_fee"]), ("https://example.com/B", 117000, 5000))
        ids = {x["candidate_id"] for x in ev}
        self.assertEqual(len(ids), 3)

    def test_exclusion_reasons(self):
        cases = {
            "SHIPPING_UNVERIFIED": (html(offer(1000, "https://example.com/x", "x")), {}),
            "VARIANT_NOT_VERIFIED_EQUAL": (html(offer(1000, "https://example.com/x", "x", 0), color="white"), {}),
            "MODEL_NOT_VERIFIED_EQUAL": (html(offer(1000, "https://example.com/x", "x", 0), model="SYN-2"), {}),
            "CONDITION_UNKNOWN_OR_NOT_NEW": (html(offer(1000, "https://example.com/x", "x", 0,
                                                       itemCondition="https://schema.org/UsedCondition")), {}),
            "OBSERVED_AT_MISSING_OR_NO_TIMEZONE": (html(offer(1000, "https://example.com/x", "x", 0)),
                                                   {"observed_at": "2026-11-05T11:00:00"}),
            "OBSERVED_AT_STALE": (html(offer(1000, "https://example.com/x", "x", 0)),
                                  {"observed_at": "2026-11-04T11:00:00+09:00"}),
            "OBSERVED_AT_FUTURE": (html(offer(1000, "https://example.com/x", "x", 0)),
                                   {"observed_at": "2026-11-05T13:00:00+09:00"}),
            "OFFER_URL_INVALID": (html(offer(1000, "http://example.com/x", "x", 0)), {}),
            "PRICE_INVALID": (html(offer(True, "https://example.com/x", "x", 0)), {}),
            "CURRENCY_NOT_KRW_OR_MISSING": (html(offer(1000, "https://example.com/x", "x", 0, priceCurrency="USD")), {}),
        }
        for code, (h, over) in cases.items():
            with self.subTest(code=code):
                m = meta(offer_terms=terms(("https://example.com/x", "normal"), ("http://example.com/x", "normal")), **over)
                _, ev, sel = pick(h, m)
                self.assertEqual(sel["status"], "NO_ELIGIBLE_CANDIDATE")
                self.assertIn(code, ev[0]["exclusion_reasons"])
                self.assertTrue(sel["excluded"][0]["reasons"])

    def test_defence_in_depth_rejects_tampered_candidate(self):
        _, ev, _ = pick(ABC_HTML, meta(offer_terms=ABC_TERMS))
        bad = copy.deepcopy([x for x in ev if x["seller_name"] == "A"][0])
        bad.update(review_issues=[], total_price=1, base_price="119000", shipping_fee=None)
        re = ad.evaluate_candidates(TARGET, [bad], now=NOW)[0]
        for code in ("PRICE_INVALID", "SHIPPING_UNVERIFIED", "TOTAL_NOT_COMPUTABLE"):
            self.assertIn(code, re["exclusion_reasons"])

    def test_tie_is_deterministic_and_reported(self):
        h = html(offer(100000, "https://example.com/A", "A", 0), offer(95000, "https://example.com/B", "B", 5000))
        m = meta(offer_terms=terms(("https://example.com/A", "normal"), ("https://example.com/B", "normal")))
        first = pick(h, m)[2]
        # Same total 100000: tie-break is lower base price, then candidate_id. B (95000+5000) wins.
        self.assertEqual(first["selected"]["seller_name"], "B")
        self.assertEqual(len(first["ties"]), 1)
        self.assertEqual(first, pick(h, m)[2])

    def test_evidence_kind_rules(self):
        with self.assertRaises(ValueError):
            ad.check_evidence_kind("synthetic", "MANUAL_IMPORT")
        with self.assertRaises(ValueError):
            ad.check_evidence_kind("user_recorded", "DEMO")
        with self.assertRaises(ValueError):
            ad.check_evidence_kind("live_verified", "MANUAL_IMPORT")
        with self.assertRaises(ValueError):
            ad.normalize_snapshot_candidates({"candidates": []}, evidence_kind="live_verified", collected_at="x")


class PanelInput(unittest.TestCase):
    """Acceptance 5, 8 — v1.0 record mapping."""

    def test_selected_maps_total_and_keeps_flags_false(self):
        _, _, sel = pick(ABC_HTML, meta(offer_terms=ABC_TERMS))
        rec = ad.to_panel_input(TARGET, sel, evidence_kind="user_recorded")
        self.assertIs(type(rec["danawa_price"]), int)
        self.assertEqual(rec["danawa_price"], 119000)
        self.assertEqual(rec["danawa_url"], "https://example.com/A")
        self.assertEqual(rec["danawa_observed_at"], OBS)
        self.assertIn("상품가 119,000원 + 배송비 0원 = 119,000원", rec["danawa_condition"])
        self.assertIn("전체 시장 최저가 보장 아님", rec["danawa_condition"])
        self.assertFalse(rec["danawa_match_checked"])
        self.assertFalse(rec["danawa_terms_checked"])
        self.assertIsNone(rec["naver_price"])
        self.assertIsNone(rec["naver_url"])
        norm = normalize_records([rec])[0]
        self.assertEqual(norm["danawa_price"], 119000)
        self.assertEqual(norm["input_issues"], [])

    def test_no_selection_is_none_not_zero(self):
        _, _, sel = pick(ABC_HTML, meta())
        rec = ad.to_panel_input(TARGET, sel, evidence_kind="user_recorded")
        self.assertIsNone(rec["danawa_price"])
        self.assertIsNone(rec["danawa_url"])
        self.assertIn("적합 후보 없음", rec["danawa_condition"])
        self.assertIn("SHIPPING_UNVERIFIED", rec["danawa_condition"])

    def test_synthetic_condition_labelled(self):
        _, _, sel = pick(ABC_HTML, meta(offer_terms=ABC_TERMS), kind="synthetic", demo=True)
        self.assertEqual(sel["selected"]["seller_name"], "A")
        self.assertIn("DEMO_ONLY", sel["selected"]["review_issues"])
        rec = ad.to_panel_input(TARGET, sel, evidence_kind="synthetic")
        self.assertTrue(rec["danawa_condition"].startswith("[합성 DEMO]"))


class BridgeE2E(unittest.TestCase):
    """Acceptance 1, 6, 7 and §7 items — full run in an isolated temporary workspace."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="snapshot_bridge_")
        self.root = Path(self.tmp.name)
        (self.root / "01_CONFIG").mkdir()
        shutil.copyfile(ROOT / "01_CONFIG/settings.example.json", self.root / "01_CONFIG/settings.example.json")
        shutil.copytree(ROOT / "07_DATA/samples", self.root / "07_DATA/samples")
        self.job = self.root / "07_DATA/samples/snapshot_demo/job.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_demo(self, jobs=None):
        return bridge.run_snapshot_to_panel(jobs or [self.job], self.root)

    def out(self, result):
        return self.root / result["output_relative"]

    def test_demo_end_to_end_seven_columns(self):
        r = self.run_demo()
        self.assertEqual((r["mode"], r["evidence_kind"], r["review_gate"], r["published"]),
                         ("DEMO", "synthetic", "DEMO_ONLY", False))
        page = (self.out(r) / "product_table.html").read_text(encoding="utf-8")
        cells = Cells()
        cells.feed(page)
        self.assertEqual(cells.headers, ["No.", "상품명", "이미지", "다나와 최저가", "사이트 주소", "네이버 최저가", "사이트 주소"])
        self.assertEqual(len(cells.rows), 3)
        self.assertEqual([row[0] for row in cells.rows], ["1", "2", "3"])
        self.assertEqual(cells.rows[0][1:], ["가상 무선 마우스 A", "IMG", "119,000원", "HREF=https://example.com/shop/a-offer https://example.com/shop/a-offer", "미수집", "미수집"])
        self.assertEqual(cells.rows[1][3:], ["미수집", "미수집", "미수집", "미수집"])
        self.assertIn("DEMO_ONLY", page)
        self.assertIn("[테스트 데이터]", page)
        self.assertIn("배송비 포함 일반 구매 총액", page)

    def test_demo_label_preserved_everywhere(self):
        r = self.run_demo()
        side = json.loads((self.root / r["sidecar"]).read_text(encoding="utf-8"))
        self.assertEqual((side["mode"], side["evidence_kind"], side["compatibility"]),
                         ("DEMO", "synthetic", "LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED"))
        self.assertEqual(side["evaluation_time_source"], "job_demo_fixed_clock")
        for p in side["products"]:
            self.assertEqual(p["probe_status"], "DEMO_ONLY")
            self.assertEqual(p["probe_review_csv_count"], 0)  # v1.3 DEMO CSV contract kept
            for c in p["candidates"]:
                self.assertEqual(c["evidence_kind"], "synthetic")
                self.assertIn("DEMO_ONLY", c["review_issues"])
            csv_path = self.out(r) / "bridge" / f"product_{p['row']:02d}_probe" / "candidates_for_review.csv"
            self.assertEqual(len(csv_path.read_text(encoding="utf-8-sig").splitlines()), 1)  # header only
        report = json.loads((self.out(r) / "run_report.json").read_text(encoding="utf-8"))
        self.assertEqual((report["mode"], report["review_gate"], report["published"]), ("DEMO", "DEMO_ONLY", False))
        rows = json.loads((self.out(r) / "normalized_products.json").read_text(encoding="utf-8"))
        self.assertTrue(all(row["danawa_condition"].startswith("[합성 DEMO]") for row in rows))

    def test_rerun_keeps_observed_at_and_does_not_publish(self):
        first = self.run_demo()
        second = self.run_demo()
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertTrue(second["reused_output"])
        rows = json.loads((self.out(second) / "normalized_products.json").read_text(encoding="utf-8"))
        self.assertEqual(rows[0]["danawa_observed_at"], OBS)
        self.assertFalse(second["published"])
        side = json.loads((self.root / second["sidecar"]).read_text(encoding="utf-8"))
        self.assertEqual(side["products"][0]["candidates"][0]["observed_at"], OBS)

    def test_partial_failure_keeps_rows(self):
        job = json.loads(self.job.read_text(encoding="utf-8"))
        job["products"][1]["meta"] = "does_not_exist.json"
        job["products"][2]["html"] = "../../../../outside.html"
        path = self.job.with_name("job_partial.json")
        path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        r = self.run_demo([path])
        self.assertEqual([p["status"] for p in r["products"]], ["SELECTED", "SNAPSHOT_FAILED", "SNAPSHOT_FAILED"])
        self.assertEqual(r["products"][0]["danawa_price"], 119000)
        side = json.loads((self.root / r["sidecar"]).read_text(encoding="utf-8"))
        self.assertIn("META_NOT_FOUND", side["products"][1]["error"])
        self.assertIn("PATH_OUTSIDE_WORKSPACE", side["products"][2]["error"])
        report = json.loads((self.out(r) / "run_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["row_count"], 3)
        self.assertIn("danawa:PRICE_MISSING", report["review"][1]["issues"])

    def test_no_structured_offers_reason_visible(self):
        r = self.run_demo()
        self.assertEqual(r["products"][2]["status"], "NO_CANDIDATE")
        rows = json.loads((self.out(r) / "normalized_products.json").read_text(encoding="utf-8"))
        self.assertIn("NO_JSONLD_PRODUCT_FOUND", rows[2]["danawa_condition"])

    def test_manual_import_requires_user_recorded_and_stays_hold(self):
        job = json.loads(self.job.read_text(encoding="utf-8"))
        bad = self.job.with_name("job_bad.json")
        bad.write_text(json.dumps({**job, "mode": "MANUAL_IMPORT"}, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):  # synthetic evidence cannot leave DEMO
            self.run_demo([bad])
        manual = {**job, "mode": "MANUAL_IMPORT", "evidence_kind": "user_recorded"}
        bad.write_text(json.dumps(manual, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):  # fixed clock is DEMO-only
            self.run_demo([bad])
        manual.pop("evaluation_time")
        manual["products"] = manual["products"][:1]
        bad.write_text(json.dumps(manual, ensure_ascii=False), encoding="utf-8")
        meta_path = self.job.with_name("product_a_meta.json")
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        m["observed_at"] = (datetime.now(KST) - timedelta(minutes=10)).isoformat(timespec="seconds")
        meta_path.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        r = self.run_demo([bad])
        self.assertEqual(r["products"][0]["danawa_price"], 119000)
        self.assertEqual(r["review_gate"], "HOLD")  # human flags are not auto-set
        report = json.loads((self.out(r) / "run_report.json").read_text(encoding="utf-8"))
        self.assertIn("danawa:MATCH_NOT_REVIEWED", report["review"][0]["issues"])
        self.assertIn("danawa:TERMS_NOT_REVIEWED", report["review"][0]["issues"])

    def test_job_validation(self):
        bad = self.job.with_name("job_v.json")
        for payload, code in (({"schema_version": "x"}, "JOB_SCHEMA_INVALID"),
                              ({"schema_version": "snapshot_job.1", "products": []}, "JOB_PRODUCTS_REQUIRED")):
            bad.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, code):
                self.run_demo([bad])
        outside = Path(tempfile.gettempdir()) / "outside_job_p01.json"
        with self.assertRaisesRegex(ValueError, "PATH_OUTSIDE_WORKSPACE"):
            self.run_demo([outside])

    def test_target_mismatch_between_job_and_meta_holds(self):
        job = json.loads(self.job.read_text(encoding="utf-8"))
        job["products"][0]["model"] = "OTHER-MODEL"
        path = self.job.with_name("job_mm.json")
        path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        r = self.run_demo([path])
        self.assertEqual(r["products"][0]["status"], "SNAPSHOT_FAILED")
        self.assertIsNone(r["products"][0]["danawa_price"])

    def test_html_escape_of_untrusted_names(self):
        job = json.loads(self.job.read_text(encoding="utf-8"))
        meta_path = self.job.with_name("product_a_meta.json")
        m = json.loads(meta_path.read_text(encoding="utf-8"))
        m["target"]["query"] = "<script>alert(1)</script>"
        meta_path.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        job["products"][0]["query"] = "<script>alert(1)</script>"
        path = self.job.with_name("job_x.json")
        path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        r = self.run_demo([path])
        page = (self.out(r) / "product_table.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)


if __name__ == "__main__":
    unittest.main()
