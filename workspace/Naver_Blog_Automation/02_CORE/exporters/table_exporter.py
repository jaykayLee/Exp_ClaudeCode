"""Offline seven-column HTML table exporter (Step 4).

Accepts objects (including ProductResult dataclasses) or mappings with:
query, image_path, danawa_price, danawa_url, naver_price, naver_url.
Does not download, resize, scrape, or publish anything.
"""
from __future__ import annotations

import base64
from collections.abc import Iterable, Mapping
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes

HEADERS = (
    "No.", "상품명", "이미지", "다나와 최저가", "사이트 주소",
    "네이버 최저가", "사이트 주소",
)
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_IMAGE_SIZE = 5 * 1024 * 1024  # resized images only; max 5 MiB each


def _field(product: object, name: str) -> object:
    if isinstance(product, Mapping):
        return product.get(name)
    return getattr(product, name, None)


def _price(value: object) -> str:
    # Do not silently use free-form scraped text: collectors must normalize to int.
    if type(value) is int and value > 0:
        return f"{value:,}원"
    return "미수집"


def _link(value: object) -> str:
    if not isinstance(value, str):
        return '<span class="missing">미수집</span>'
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return '<span class="missing">유효하지 않은 URL</span>'
    if parts.scheme.lower() not in ("https", "http") or not parts.netloc or parts.username:
        return '<span class="missing">유효하지 않은 URL</span>'
    cleaned = escape(value.strip(), quote=True)
    return f'<a href="{cleaned}" target="_blank" rel="noopener noreferrer">{cleaned}</a>'


def _image(value: object, alt: str, image_base_dir: Path) -> str:
    if not isinstance(value, (str, Path)) or not str(value):
        return '<span class="missing">이미지 없음</span>'
    file_path = Path(value).expanduser()
    if not file_path.is_absolute():
        file_path = image_base_dir / file_path
    try:
        file_path = file_path.resolve()
        file_path.relative_to(image_base_dir.resolve())
    except (ValueError, OSError):
        return '<span class="missing">이미지 경로 범위 초과</span>'
    mime, _ = mimetypes.guess_type(file_path.name)
    if mime not in _IMAGE_TYPES:
        return '<span class="missing">이미지 형식 불가</span>'
    try:
        if not file_path.is_file() or file_path.stat().st_size > _MAX_IMAGE_SIZE:
            return '<span class="missing">이미지 없음/크기 초과</span>'
        content = file_path.read_bytes()
    except OSError:
        return '<span class="missing">이미지 읽기 실패</span>'
    b64 = base64.b64encode(content).decode("ascii")
    return (f'<img src="data:{mime};base64,{b64}" '
            f'alt="{escape(alt, quote=True)}" loading="lazy">')


def render_product_table(
    products: Iterable[object],
    image_base_dir: str | Path | None = None,
    title: str = "상품 가격 비교표",
) -> str:
    """Return a portable HTML preview with 7 exact headers and embedded images."""
    base = Path(image_base_dir) if image_base_dir is not None else Path.cwd()
    rows = []
    for i, product in enumerate(products, 1):
        query = str(_field(product, "query") or "미입력")
        cells = (
            escape(str(i)),
            escape(query),
            _image(_field(product, "image_path"), query, base),
            escape(_price(_field(product, "danawa_price"))),
            _link(_field(product, "danawa_url")),
            escape(_price(_field(product, "naver_price"))),
            _link(_field(product, "naver_url")),
        )
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    if not rows:
        rows = ['<tr><td colspan="7">상품 데이터가 없습니다.</td></tr>']
    header_html = "".join(f"<th>{escape(h)}</th>" for h in HEADERS)
    body_html = "\n".join(rows)
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
body{{font-family:Arial,"Malgun Gothic",sans-serif;margin:24px;color:#182230;background:#f6f8fb}}
h1{{font-size:23px}}.note{{font-size:13px;color:#596579}}
.table-wrap{{overflow-x:auto;background:white;border:1px solid #dce3ec;border-radius:10px}}
table{{border-collapse:collapse;width:100%;min-width:1030px;font-size:13px}}
th{{text-align:center;background:#e8eef7;padding:13px 9px;white-space:nowrap}}
td{{border-top:1px solid #e5eaf0;padding:10px;vertical-align:middle;word-break:break-all}}
td:first-child{{text-align:center;width:42px}}td:nth-child(3){{text-align:center;min-width:120px}}
img{{display:block;margin:auto;width:100px;height:130px;object-fit:contain;background:#fff}}
a{{color:#1256ad}}.missing{{color:#8b929e}}
</style></head><body>
<h1>{escape(title)}</h1>
<p class="note">오프라인 검증용 미리보기입니다. 실제 네이버 블로그 게시물 등록과는 별도 단계입니다.</p>
<div class="table-wrap"><table><thead><tr>{header_html}</tr></thead>
<tbody>{body_html}</tbody></table></div></body></html>
'''


def export_product_table(
    products: Iterable[object],
    output_file: str | Path = "output/product_table.html",
    image_base_dir: str | Path | None = None,
    title: str = "상품 가격 비교표",
) -> Path:
    """Write UTF-8 HTML and return its absolute path."""
    output = Path(output_file).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_product_table(products, image_base_dir=image_base_dir, title=title),
        encoding="utf-8",
    )
    return output
