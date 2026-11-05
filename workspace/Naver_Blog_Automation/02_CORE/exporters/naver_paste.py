"""Paste-test table for the Naver blog editor (P06). Additive module; table_exporter is unchanged.

Editors commonly drop <style>, classes and data: images, so this file uses inline styles only and
puts the upload file name in the image column instead of an embedded image. Whether the current
Naver editor keeps this markup is NOT verified — the guide says to paste one row first.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from .table_exporter import HEADERS

_TD = 'style="border:1px solid #cccccc;padding:6px 8px;vertical-align:middle"'
_TH = 'style="border:1px solid #cccccc;padding:6px 8px;background:#f2f4f7;font-weight:bold"'
GATE_TEXT = {
    "DEMO_ONLY": "데모 자료 — 게시 금지 (가격·링크 모두 가상)",
    "HOLD": "검토 보류 — 보류 사유 해결 전 게시 금지",
    "READY_FOR_MANUAL_REVIEW": "형식 검사 통과 — 게시 전 사람이 출처·조건을 다시 확인",
}


def _price(value: object) -> str:
    return f"{value:,}원" if type(value) is int and value > 0 else "미수집"


def _link(value: object) -> str:
    if not isinstance(value, str):
        return "미수집"
    parts = urlsplit(value.strip())
    if parts.scheme not in ("https", "http") or not parts.netloc or parts.username:
        return "미수집"
    url = escape(value.strip(), quote=True)
    return f'<a href="{url}">{url}</a>'


def render_naver_paste(rows: list[dict], gate: str, *, run_id: str = "") -> str:
    body = []
    for i, row in enumerate(rows, 1):
        image = f"images/product_{i:02d}.jpg 업로드" if row.get("image_path") else "이미지 없음"
        cells = (str(i), escape(str(row.get("query") or "")), escape(image),
                 _price(row.get("danawa_price")), _link(row.get("danawa_url")),
                 _price(row.get("naver_price")), _link(row.get("naver_url")))
        body.append("<tr>" + "".join(f"<td {_TD}>{c}</td>" for c in cells) + "</tr>")
    head = "".join(f"<th {_TH}>{escape(h)}</th>" for h in HEADERS)
    notice = escape(GATE_TEXT.get(gate, gate))
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>네이버 에디터 붙여넣기 시험용 표</title></head>
<body style="font-family:'Malgun Gothic',Arial,sans-serif;margin:24px">
<p style="color:#9a3412;font-weight:bold">[{escape(gate)}] {notice}</p>
<p style="color:#555555;font-size:13px">이 안내 문단은 복사하지 마세요. 아래 표에서 <b>1행만 먼저</b> 복사해 네이버 글쓰기 화면에 붙여넣고,
열·링크 유지 여부를 확인합니다. 이미지는 같은 실행 폴더의 images/ 파일을 글쓰기 도구로 직접 업로드합니다.
표의 최저가는 확인한 적합 후보 범위의 값이며 전체 시장 최저가가 아닙니다. 실행 ID: {escape(run_id)}</p>
<table style="border-collapse:collapse;font-size:14px"><thead><tr>{head}</tr></thead>
<tbody>{''.join(body)}</tbody></table>
</body></html>
"""


def write_naver_paste(output_dir: Path, rows: list[dict], gate: str, *, run_id: str = "") -> Path:
    path = Path(output_dir) / "naver_paste_table.html"
    path.write_text(render_naver_paste(rows, gate, run_id=run_id), encoding="utf-8")
    return path


def write_for_run(root: Path, summary: dict) -> str:
    """Create the paste table for a finished v1.0 pipeline run; returns its preview URL."""
    import json
    out = Path(root) / summary["output_relative"]
    rows = json.loads((out / "normalized_products.json").read_text(encoding="utf-8"))
    write_naver_paste(out, rows, summary["review_gate"], run_id=summary["run_id"])
    return "/output/" + summary["run_id"] + "/naver_paste_table.html"
