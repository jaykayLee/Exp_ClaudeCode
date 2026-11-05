"""P04 browser E2E: real LocalServer over HTTP + Chromium clicks. Synthetic data, temp copy of the workspace.

Run from handoff root (needs Playwright for Python; dev-only, not in dependencies.lock):
  workspace/Naver_Blog_Automation/.venv/bin/python 00_SESSION/evidence/P04/ui_snapshot_e2e.py
"""
from __future__ import annotations
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[2] / "workspace/Naver_Blog_Automation"
sys.path.insert(0, str(APP / "tools"))
from environment import ROOT  # noqa: E402
from server import LocalServer  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

import os
# Cloud sessions ship Chromium here; elsewhere (CI, user PC) use Playwright's own browser.
CHROME = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
checks, errors = [], []


def ok(name, cond, detail=""):
    checks.append({"name": name, "passed": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + name, detail)


with tempfile.TemporaryDirectory(prefix="p04_ui_") as temp:
    root = Path(temp) / "작업 폴더 Naver_Blog_Automation"  # space + Korean in path on purpose
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "08_OUTPUT", "09_LOGS"))
    server = LocalServer(("127.0.0.1", 0), root)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = "http://" + server.authority + "/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME, headless=True)
            # bypass_csp only lets the test harness evaluate wait conditions; the app CSP itself is unchanged.
            ctx = dict(bypass_csp=True, device_scale_factor=2)
            page = browser.new_page(viewport={"width": 1280, "height": 900}, **ctx)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: d.accept())
            page.goto(url)
            page.wait_for_function("document.querySelector('#connection').textContent.includes('로컬 서버 연결')")
            ok("connected_real_http", True, url)
            page.locator("#snapshotDemoButton").click()
            page.wait_for_function("document.querySelectorAll('#snapshotRows tr').length===3 && document.querySelector('#snapshotRows').innerText.includes('선택됨')")
            rows = page.locator("#snapshotRows").inner_text()
            ok("status_rows_three", page.locator("#snapshotRows tr").count() == 3)
            ok("row1_selected_total", "총액 119,000원" in rows)
            ok("row2_hold_reason_korean", "배송비 미확인" in rows)
            ok("row3_no_structured", "구조화된 상품 정보 없음" in rows)
            ok("naver_not_connected_shown", rows.count("미연결") == 3)
            ok("badge_demo", "DEMO" in page.locator("#snapshotBadge").inner_text())
            card = page.locator("#snapshotCard")
            card.scroll_into_view_if_needed()
            card.screenshot(path=str(HERE / "panel_snapshot_card.png"))
            page.locator("#snapshotLoadButton").click()
            page.wait_for_function("document.querySelectorAll('#productRows tr').length===3")
            table = page.locator("#productRows").inner_text()
            ok("loaded_into_review_list", "119,000원" in table and "가상 키보드 B" in table)
            ok("mode_badge_demo", "DEMO" in page.locator("#modeBadge").inner_text())
            page.locator("#workbench .card.working").screenshot(path=str(HERE / "panel_review_list.png"))
            page.locator("#productRows [data-edit='0']").click()
            dialog = page.locator("#productDialog")
            ok("human_check_unticked", not dialog.locator("[name=danawa_match_checked]").is_checked()
               and not dialog.locator("[name=danawa_terms_checked]").is_checked())
            dialog.screenshot(path=str(HERE / "panel_edit_dialog.png"))
            page.locator("#cancelDialog").click()
            href = page.locator("#snapshotStatus a").get_attribute("href")
            table_page = browser.new_page(viewport={"width": 1200, "height": 900}, **ctx)
            table_page.goto(url.rstrip("/") + href)
            ths = table_page.locator("thead th").all_inner_texts()
            ok("generated_table_seven_headers", ths == ["No.", "상품명", "이미지", "다나와 최저가", "사이트 주소", "네이버 최저가", "사이트 주소"], str(ths))
            table_page.screenshot(path=str(HERE / "generated_table.png"), full_page=True)
            mobile = browser.new_page(viewport={"width": 390, "height": 844}, **ctx)
            mobile.on("pageerror", lambda e: errors.append(str(e)))
            mobile.goto(url)
            mobile.wait_for_function("document.querySelector('#connection').textContent.includes('로컬 서버 연결')")
            mobile.locator("#snapshotDemoButton").click()
            mobile.wait_for_function("document.querySelector('#snapshotRows').innerText.includes('선택됨')")
            overflow = mobile.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            ok("mobile_no_page_horizontal_overflow", overflow <= 1, f"overflow={overflow}px")
            scrollable = mobile.evaluate("(()=>{const w=document.querySelector('#snapshotRows').closest('.tablewrap');return getComputedStyle(w).overflowX==='auto' && w.scrollWidth>w.clientWidth;})()")
            ok("mobile_status_table_scrolls_inside_card", scrollable)
            mobile.locator("#snapshotCard").screenshot(path=str(HERE / "panel_snapshot_card_mobile.png"))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

ok("no_javascript_errors", not errors, "; ".join(errors)[:300])
result = {"passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks,
          "path_with_space_and_korean": True, "windows_browser_tested": False}
(HERE / "ui_snapshot_e2e.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("passed", "total")}))
raise SystemExit(0 if result["passed"] == result["total"] else 1)
