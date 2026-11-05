"""P06 tests: install ZIP builder (no user data leaks) and the Naver paste-test table."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from environment import ROOT
import build_release
import run_snapshot_to_panel as bridge
from exporters.naver_paste import render_naver_paste

HEADERS7 = ["No.", "상품명", "이미지", "다나와 최저가", "사이트 주소", "네이버 최저가", "사이트 주소"]


class ReleaseBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="release_p06_")
        base = Path(self.tmp.name)
        self.root = base / "Naver_Blog_Automation"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "08_OUTPUT"))
        # Simulate a used workspace full of private/runtime data.
        planted = {
            "01_CONFIG/settings.local.json": '{"auto_publish": false}',
            "07_DATA/inbox/products.json": '{"records": [{"query": "내 실제 상품"}]}',
            "07_DATA/inbox/snapshot_job.json": "{}",
            "07_DATA/images/original/abc.jpg": "x",
            "07_DATA/images/resized/abc.jpg": "x",
            "07_DATA/state/latest_run.json": "{}",
            "07_DATA/state/pipeline.lock": "{}",
            "08_OUTPUT/runs/20261105_x/product_table.html": "x",
            "09_LOGS/install_1.log": "x", "09_LOGS/daily/run_1.json": "{}",
            "04_CONTENT/briefs/brief_1.md": "x",
            ".venv/Scripts/python.exe": "x",
            "tools/__pycache__/a.pyc": "x",
            "11_ADDONS/DANAWA_SNAPSHOT_PROBE/output/manual/snapshot_report.json": "{}",
        }
        for rel, text in planted.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        self.planted = planted
        self.out = base / "배포 dist"

    def tearDown(self):
        self.tmp.cleanup()

    def test_zip_excludes_user_data_and_has_entrypoints(self):
        info = build_release.build(self.root, self.out, "test")
        with zipfile.ZipFile(info["zip"]) as z:
            names = {n.split("/", 1)[1] for n in z.namelist()}
            for rel in self.planted:
                if rel != "07_DATA/inbox/products.json":
                    self.assertNotIn(rel, names)
            self.assertEqual(json.loads(z.read("Naver_Blog_Automation/07_DATA/inbox/products.json")), {"records": []})
            for rel in build_release.REQUIRED:
                self.assertIn(rel, names)
            self.assertEqual(len([n for n in names if n.endswith(".bat") and "/" not in n]), 10)
            manifest = json.loads(z.read("Naver_Blog_Automation/00_PROJECT/RELEASE_MANIFEST.json"))
            for item in manifest["files"]:
                self.assertEqual(hashlib.sha256(z.read("Naver_Blog_Automation/" + item["path"])).hexdigest(), item["sha256"])
            self.assertIn("07_DATA/images/original/README.md", names)
            self.assertIn("09_LOGS/README.md", names)

    def test_rebuild_from_installed_copy(self):
        """Regression (found in P06 clean-install check): an old manifest must not be re-packed."""
        first = build_release.build(self.root, self.out, "one")
        with zipfile.ZipFile(first["zip"]) as z:
            (self.root / "00_PROJECT/RELEASE_MANIFEST.json").write_bytes(z.read("Naver_Blog_Automation/00_PROJECT/RELEASE_MANIFEST.json"))
        second = build_release.build(self.root, self.out, "two")
        with zipfile.ZipFile(second["zip"]) as z:
            manifest = json.loads(z.read("Naver_Blog_Automation/00_PROJECT/RELEASE_MANIFEST.json"))
            self.assertNotIn("00_PROJECT/RELEASE_MANIFEST.json", [i["path"] for i in manifest["files"]])
            for item in manifest["files"]:
                self.assertEqual(hashlib.sha256(z.read("Naver_Blog_Automation/" + item["path"])).hexdigest(), item["sha256"])

    def test_output_inside_workspace_refused(self):
        with self.assertRaisesRegex(ValueError, "OUTPUT_INSIDE_WORKSPACE"):
            build_release.build(self.root, self.root / "dist", "x")

    def test_secret_like_value_blocks_build(self):
        fake = '{"api' + '_key": "' + 'abcd1234' + 'efgh5678ijkl"}'   # assembled so this source file stays clean
        (self.root / "04_CONTENT/notes.json").write_text(fake, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SECRET_LIKE_VALUE_FOUND"):
            build_release.build(self.root, self.out, "x")


class NaverPaste(unittest.TestCase):
    def test_inline_only_seven_columns(self):
        rows = [{"query": "<b>상품</b>", "image_path": "x.jpg", "danawa_price": 119000,
                 "danawa_url": "https://example.com/a?x=1&y=2", "naver_price": None, "naver_url": None}]
        page = render_naver_paste(rows, "HOLD", run_id="r1")
        self.assertEqual(re.findall(r"<th [^>]*>(.*?)</th>", page), HEADERS7)
        self.assertNotIn("<img", page)
        self.assertNotIn("base64", page)
        self.assertNotIn("<script", page)
        self.assertNotIn("<style", page)
        self.assertNotIn("class=", page)
        self.assertIn("&lt;b&gt;상품&lt;/b&gt;", page)
        self.assertIn("119,000원", page)
        self.assertIn("images/product_01.jpg 업로드", page)
        self.assertIn('href="https://example.com/a?x=1&amp;y=2"', page)
        self.assertIn("게시 금지", page)
        self.assertEqual(page.count("미수집"), 2)

    def test_written_by_bridge_demo(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "01_CONFIG").mkdir()
            shutil.copyfile(ROOT / "01_CONFIG/settings.example.json", root / "01_CONFIG/settings.example.json")
            shutil.copytree(ROOT / "07_DATA/samples", root / "07_DATA/samples")
            result = bridge.run_snapshot_to_panel([root / bridge.DEMO_JOB], root)
            page = (root / result["output_relative"] / "naver_paste_table.html").read_text(encoding="utf-8")
            self.assertIn("[DEMO_ONLY]", page)
            self.assertTrue(result["paste_url"].endswith("/naver_paste_table.html"))


if __name__ == "__main__":
    unittest.main()
