"""P04 tests: snapshot bridge inside the local panel, image integrity, status display, human review loop.

Synthetic data only. No network. Browser rendering is checked separately (screenshot evidence).
"""
from __future__ import annotations

import hashlib
import http.client
import json
import re
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from environment import ROOT
from server import LocalServer
import run_snapshot_to_panel as bridge
from nbcore.pipeline import run_pipeline

KST = timezone(timedelta(hours=9))
HEADERS7 = ["No.", "상품명", "이미지", "다나와 최저가", "사이트 주소", "네이버 최저가", "사이트 주소"]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="panel_p04_")
        self.root = Path(self.tmp.name)
        (self.root / "01_CONFIG").mkdir()
        shutil.copyfile(ROOT / "01_CONFIG/settings.example.json", self.root / "01_CONFIG/settings.example.json")
        shutil.copytree(ROOT / "07_DATA/samples", self.root / "07_DATA/samples")
        shutil.copytree(ROOT / "06_UI", self.root / "06_UI")
        self.demo_job = self.root / "07_DATA/samples/snapshot_demo/job.json"

    def tearDown(self):
        self.tmp.cleanup()

    def user_recorded_job(self, minutes_ago=10, **product_override):
        """A MANUAL_IMPORT job made from the synthetic fixture, re-labelled as a user record for testing."""
        inbox = self.root / "07_DATA/inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        src = self.root / "07_DATA/samples/snapshot_demo"
        shutil.copyfile(src / "product_a.html", inbox / "a.html")
        meta = json.loads((src / "product_a_meta.json").read_text(encoding="utf-8"))
        meta["observed_at"] = (datetime.now(KST) - timedelta(minutes=minutes_ago)).isoformat(timespec="seconds")
        (inbox / "a_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        product = {"query": "가상 무선 마우스 A", "html": "a.html", "meta": "a_meta.json",
                   "image_path": "07_DATA/samples/transparent.png", "image_rights": "owned", "image_credit": "테스트 도형"}
        product.update(product_override)
        job = {"schema_version": "snapshot_job.1", "mode": "MANUAL_IMPORT", "evidence_kind": "user_recorded",
               "products": [product]}
        path = inbox / "snapshot_job.json"
        path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        return path


class ServerSnapshotApi(Base):
    def setUp(self):
        super().setUp()
        self.server = LocalServer(("127.0.0.1", 0), self.root)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def request(self, method, path, body=None, token=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=15)
        headers = {"Host": self.server.authority}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["X-Workspace-Token"] = self.server.token
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        r = conn.getresponse()
        data = r.read()
        conn.close()
        return r.status, data

    def test_demo_snapshot_via_api(self):
        code, data = self.request("POST", "/api/snapshot", {"demo": True})
        self.assertEqual(code, 200, data)
        result = json.loads(data)
        self.assertEqual((result["mode"], result["review_gate"]), ("DEMO", "DEMO_ONLY"))
        self.assertEqual([r["danawa_status"] for r in result["status_rows"]],
                         ["SELECTED", "NO_ELIGIBLE_CANDIDATE", "NO_CANDIDATE"])
        self.assertIn("총액 119,000원", result["status_rows"][0]["detail"])
        self.assertIn("배송비 미확인", result["status_rows"][1]["detail"])
        self.assertIn("구조화된 상품 정보 없음", result["status_rows"][2]["detail"])
        self.assertTrue(all(r["naver_status"] == "NOT_CONNECTED" for r in result["status_rows"]))
        self.assertEqual(len(result["panel_records"]), 3)
        self.assertEqual(self.request("GET", result["pipeline"]["preview_url"])[0], 200)
        side_url = "/output/" + result["sidecar"].split("08_OUTPUT/runs/", 1)[1]
        code, side = self.request("GET", side_url)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(side)["evidence_kind"], "synthetic")

    def test_snapshot_api_guards(self):
        self.assertEqual(self.request("POST", "/api/snapshot", {"demo": True}, token=False)[0], 403)
        for job in ("../../etc/passwd.json", "06_UI/x.json", "07_DATA/inbox/x.txt", 5):
            code, data = self.request("POST", "/api/snapshot", {"job": job})
            self.assertEqual(code, 400, job)
        code, data = self.request("POST", "/api/snapshot", {"job": "07_DATA/inbox/missing.json"})
        self.assertEqual(code, 400)
        self.assertIn("JOB_NOT_FOUND", json.loads(data)["error"])

    def test_user_recorded_job_via_api(self):
        self.user_recorded_job()
        code, data = self.request("POST", "/api/snapshot", {"job": "07_DATA/inbox/snapshot_job.json"})
        self.assertEqual(code, 200, data)
        result = json.loads(data)
        self.assertEqual((result["mode"], result["evidence_kind"], result["review_gate"]),
                         ("MANUAL_IMPORT", "user_recorded", "HOLD"))
        self.assertEqual(result["panel_records"][0]["danawa_price"], 119000)


class HumanReviewLoop(Base):
    """I13: bridge -> panel list -> a person ticks checks -> MANUAL_IMPORT run."""

    def test_checked_record_clears_danawa_issues_naver_still_missing(self):
        job = self.user_recorded_job()
        result = bridge.run_for_panel(job, self.root)
        record = dict(result["panel_records"][0])
        self.assertFalse(record["danawa_match_checked"])
        record["danawa_match_checked"] = True   # what the person does in the dialog
        record["danawa_terms_checked"] = True
        summary = run_pipeline(self.root, [record], "MANUAL_IMPORT")
        issues = summary["review"][0]["issues"]
        self.assertFalse([i for i in issues if i.startswith("danawa:")], issues)
        self.assertIn("naver:PRICE_MISSING", issues)    # Naver source not connected (P03)
        self.assertEqual(summary["review_gate"], "HOLD")
        rows = json.loads((self.root / summary["output_relative"] / "normalized_products.json").read_text(encoding="utf-8"))
        self.assertEqual(rows[0]["danawa_observed_at"], record["danawa_observed_at"])


class ImageIntegrity(Base):
    def sha(self, p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def test_originals_unchanged_and_outputs_354x472(self):
        samples = {n: self.sha(self.root / "07_DATA/samples" / n) for n in ("landscape.png", "portrait.png", "transparent.png")}
        result = bridge.run_snapshot_to_panel([self.demo_job], self.root)
        out = self.root / result["output_relative"] / "images"
        files = sorted(out.glob("product_*.jpg"))
        self.assertEqual(len(files), 3)
        for f in files:
            with Image.open(f) as im:
                self.assertEqual(im.size, (354, 472))
                self.assertEqual(im.mode, "RGB")
                dpi = im.info.get("dpi")
                self.assertEqual(tuple(round(x) for x in dpi), (300, 300))
        with Image.open(files[2]) as im:  # transparent sample -> white padding, not black
            self.assertEqual(im.getpixel((2, 2)), (255, 255, 255))
        with Image.open(files[0]) as im:  # landscape keeps ratio: top/bottom white margin
            self.assertEqual(im.getpixel((177, 3)), (255, 255, 255))
        for name, digest in samples.items():
            self.assertEqual(self.sha(self.root / "07_DATA/samples" / name), digest)

    def test_broken_or_missing_image_keeps_price_row(self):
        (self.root / "07_DATA/samples/broken.png").write_bytes(b"not an image")
        for image in ("07_DATA/samples/broken.png", "07_DATA/samples/none.png", "../../outside.png"):
            with self.subTest(image=image):
                job = self.user_recorded_job(image_path=image)
                result = bridge.run_snapshot_to_panel([job], self.root)
                self.assertEqual(result["products"][0]["danawa_price"], 119000)
                report = json.loads((self.root / result["output_relative"] / "run_report.json").read_text(encoding="utf-8"))
                self.assertTrue(any(i.startswith("IMAGE_ERROR") or i == "IMAGE_MISSING" for i in report["review"][0]["issues"]))
                page = (self.root / result["output_relative"] / "product_table.html").read_text(encoding="utf-8")
                self.assertIn("119,000원", page)


class StaticUi(unittest.TestCase):
    def setUp(self):
        self.page = (ROOT / "06_UI/index.html").read_text(encoding="utf-8")

    def test_required_table_headers_unchanged(self):
        thead = re.search(r'<table class="requiredtable"><thead><tr>(.*?)</tr>', self.page).group(1)
        self.assertEqual(re.findall(r"<th>(.*?)</th>", thead), HEADERS7)

    def test_snapshot_card_present_and_offline(self):
        for element in ("snapshotDemoButton", "snapshotRunButton", "snapshotRows", "snapshotLoadButton"):
            self.assertIn(f'id="{element}"', self.page)
        self.assertNotRegex(self.page, r'<script[^>]+src=')
        self.assertIn("자동으로 체크하지 않습니다", self.page)


if __name__ == "__main__":
    unittest.main()
