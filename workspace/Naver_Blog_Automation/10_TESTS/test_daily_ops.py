"""P05 tests: unattended daily run (run_once), duplicate/re-run safety, and static Windows script checks.

Windows execution itself is NOT tested here (Linux). Static checks only guard known failure modes.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from environment import ROOT
import run_once
from nbcore.pipeline import pipeline_lock

KST = timezone(timedelta(hours=9))


class Daily(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="daily_p05_")
        self.root = Path(self.tmp.name) / "운영 폴더 Naver Blog"   # space + Korean on purpose
        (self.root / "01_CONFIG").mkdir(parents=True)
        shutil.copyfile(ROOT / "01_CONFIG/settings.example.json", self.root / "01_CONFIG/settings.example.json")
        shutil.copytree(ROOT / "07_DATA/samples", self.root / "07_DATA/samples")
        self.inbox = self.root / "07_DATA/inbox"
        self.inbox.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def products(self, records):
        (self.inbox / "products.json").write_text(json.dumps({"records": records}, ensure_ascii=False), encoding="utf-8")

    def snapshot_job(self):
        src = self.root / "07_DATA/samples/snapshot_demo"
        shutil.copyfile(src / "product_a.html", self.inbox / "a.html")
        meta = json.loads((src / "product_a_meta.json").read_text(encoding="utf-8"))
        meta["observed_at"] = (datetime.now(KST) - timedelta(minutes=5)).isoformat(timespec="seconds")
        (self.inbox / "a_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        job = {"schema_version": "snapshot_job.1", "mode": "MANUAL_IMPORT", "evidence_kind": "user_recorded",
               "products": [{"query": "가상 무선 마우스 A", "html": "a.html", "meta": "a_meta.json",
                             "image_path": "07_DATA/samples/landscape.png", "image_rights": "owned", "image_credit": "테스트 도형"}]}
        (self.inbox / "snapshot_job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

    def manual_record(self):
        rows = json.loads((self.root / "07_DATA/samples/products_demo.json").read_text(encoding="utf-8"))["records"]
        row = dict(rows[0])
        for s in ("danawa", "naver"):
            row[s + "_observed_at"] = (datetime.now(KST) - timedelta(minutes=5)).isoformat(timespec="seconds")
        return row

    def test_no_input_is_not_a_failure_and_is_logged(self):
        code, report = run_once.run_daily(self.root)
        self.assertEqual((code, report["overall"]), (0, "NO_INPUT"))
        self.assertTrue((self.root / report["log"]).is_file())
        self.products([])   # shipped default inbox
        code, report = run_once.run_daily(self.root)
        self.assertEqual((code, report["overall"]), (0, "NO_INPUT"))
        self.assertEqual(report["inputs"]["products"]["status"], "NO_INPUT")

    def test_both_inputs_processed_independently(self):
        self.snapshot_job()
        self.products([self.manual_record()])
        code, report = run_once.run_daily(self.root)
        self.assertEqual((code, report["overall"]), (0, "DONE"))
        self.assertEqual(report["inputs"]["snapshot_job"]["review_gate"], "HOLD")
        self.assertEqual(report["inputs"]["products"]["review_gate"], "HOLD")
        self.assertFalse(report["published"])
        logged = json.loads((self.root / report["log"]).read_text(encoding="utf-8"))
        self.assertEqual(logged["overall"], "DONE")

    def test_one_failure_keeps_other_result(self):
        self.snapshot_job()
        (self.inbox / "products.json").write_text("{broken", encoding="utf-8")
        code, report = run_once.run_daily(self.root)
        self.assertEqual((code, report["overall"]), (1, "FAILED"))
        self.assertEqual(report["inputs"]["products"]["status"], "FAILED")
        self.assertEqual(report["inputs"]["snapshot_job"]["status"], "DONE")
        self.assertTrue((self.root / report["inputs"]["snapshot_job"]["output"] / "product_table.html").is_file())

    def test_rerun_same_day_reuses_output_and_keeps_observed_at(self):
        self.snapshot_job()
        _, first = run_once.run_daily(self.root)
        _, second = run_once.run_daily(self.root)
        a, b = first["inputs"]["snapshot_job"], second["inputs"]["snapshot_job"]
        self.assertEqual(a["run_id"], b["run_id"])
        self.assertTrue(b["reused_output"])
        rows = json.loads((self.root / b["output"] / "normalized_products.json").read_text(encoding="utf-8"))
        meta = json.loads((self.inbox / "a_meta.json").read_text(encoding="utf-8"))
        self.assertEqual(rows[0]["danawa_observed_at"], meta["observed_at"])
        self.assertNotEqual(first["log"], second["log"])

    def test_concurrent_run_is_refused_and_lock_kept(self):
        self.snapshot_job()
        with pipeline_lock(self.root):
            code, report = run_once.run_daily(self.root)
            self.assertEqual(code, 1)
            entry = report["inputs"]["snapshot_job"]
            self.assertIn("PIPELINE_BUSY", entry["error"])
            self.assertEqual(entry["lock"]["pid"], os.getpid())
            self.assertGreaterEqual(entry["lock"]["age_minutes"], 0)
            self.assertTrue((self.root / run_once.LOCK).exists())   # never auto-deleted
        self.assertFalse((self.root / run_once.LOCK).exists())
        self.assertEqual(run_once.run_daily(self.root)[0], 0)

    def test_demo_modes_do_not_touch_inbox(self):
        self.products([])
        before = (self.inbox / "products.json").read_bytes()
        self.assertEqual(run_once.run_daily(self.root, demo=True)[1]["inputs"]["products_demo"]["review_gate"], "DEMO_ONLY")
        self.assertEqual(run_once.run_daily(self.root, snapshot_demo=True)[1]["inputs"]["snapshot_demo"]["review_gate"], "DEMO_ONLY")
        self.assertEqual((self.inbox / "products.json").read_bytes(), before)


class WindowsScriptsStatic(unittest.TestCase):
    """Static guards only. Real Windows execution remains NEEDS_WINDOWS_CHECK."""
    BATS = sorted(ROOT.glob("*.bat"))

    def test_bat_encoding_and_header(self):
        self.assertGreaterEqual(len(self.BATS), 10)
        for bat in self.BATS:
            with self.subTest(bat=bat.name):
                raw = bat.read_bytes()
                raw.decode("ascii")                       # ASCII-only: no codepage surprises
                self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))   # CRLF only
                text = raw.decode("ascii")
                self.assertTrue(text.startswith("@echo off\r\n"))
                self.assertIn('cd /d "%~dp0"', text)
                if "python" in text.lower() or "powershell" in text.lower():
                    self.assertIn("chcp 65001", text)   # UTF-8 console for Korean messages

    def test_bat_paths_quoted(self):
        for bat in self.BATS:
            for line in bat.read_text(encoding="ascii").splitlines():
                for m in re.finditer(r"%~dp0\S*", line):
                    with self.subTest(bat=bat.name, line=line):
                        start = m.start()
                        self.assertEqual(line[start - 1], '"', "unquoted %~dp0 path breaks on spaces")

    def test_python_entrypoints_exist(self):
        for bat in self.BATS:
            for rel in re.findall(r'%~dp0(tools\\[\w.]+)', bat.read_text(encoding="ascii")):
                self.assertTrue((ROOT / rel.replace("\\", "/")).is_file(), f"{bat.name}: {rel}")

    def test_scheduler_requires_confirmation_and_is_local_only(self):
        ps = (ROOT / "tools/schedule.ps1").read_text(encoding="utf-8")
        self.assertLess(ps.index("Read-Host 'Register this local-only task? [Y/N]'"), ps.index("Register-ScheduledTask"))
        self.assertIn("Unregister-ScheduledTask", ps)
        self.assertIn("run_once.py", ps)                 # python directly: no BAT pause in unattended runs
        self.assertIn("MultipleInstances IgnoreNew", ps)
        self.assertIn("-RunLevel Limited", ps)
        self.assertNotRegex(ps, r"(?i)password|cookie|credential")
        self.assertIn("no collection and no publication", ps)
        self.assertIn("-Remove", (ROOT / "disable_daily_review.bat").read_text(encoding="ascii") +
                      (ROOT / "tools/schedule.ps1").read_text(encoding="utf-8"))

    def test_unattended_python_never_prompts(self):
        for name in ("run_once.py", "run_snapshot_to_panel.py", "qa_runner.py", "doctor.py"):
            tree = ast.parse((ROOT / "tools" / name).read_text(encoding="utf-8"))
            calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            self.assertNotIn("input", calls, name)

    def test_installer_does_not_overwrite_user_data(self):
        ps = (ROOT / "tools/bootstrap.ps1").read_text(encoding="utf-8")
        self.assertNotRegex(ps, r"(?i)Remove-Item[^\n]*(07_DATA|01_CONFIG|settings\.local)")
        self.assertIn("Existing .venv is incompatible", ps)
        self.assertIn("--only-binary=:all:", ps)


if __name__ == "__main__":
    unittest.main()
