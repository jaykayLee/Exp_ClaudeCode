"""Offline Danawa saved-HTML evidence probe (not a crawler).

Only local HTML is read. No remote fetch, credentials, browser automation or publishing.
Tested with synthetic JSON-LD; real-site page structure is not verified.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import ipaddress
import json
import re
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

VERSION = "1.3.0"
MAX_HTML_BYTES = 5 * 1024 * 1024
MAX_JSONLD_BYTES = 1024 * 1024
MAX_ITEMS = 100
FRESH_HOURS = 24
CSV_COLUMNS = [
    "query", "model", "variant", "candidate_model", "candidate_variant",
    "base_price", "shipping_fee", "product_condition", "payment_condition",
    "url", "observed_at", "source_page", "image_path", "image_rights", "image_credit"
]


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._capturing = False
        self._parts: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            at = dict((k.lower(), v) for k, v in attrs)
            if (at.get("type") or "").strip().lower() == "application/ld+json":
                self._capturing = True
                self._parts = []

    def handle_data(self, data):
        if self._capturing:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._capturing:
            self.blocks.append("".join(self._parts))
            self._parts = []
            self._capturing = False


def is_type(obj, name: str) -> bool:
    typ = obj.get("@type", "") if isinstance(obj, dict) else ""
    types = typ if isinstance(typ, list) else [typ]
    return any(str(t).rsplit("/", 1)[-1].lower() == name.lower() for t in types)


def iter_nodes(node):
    if isinstance(node, list):
        for x in node:
            yield from iter_nodes(x)
    elif isinstance(node, dict):
        yield node
        if "@graph" in node:
            yield from iter_nodes(node["@graph"])


def read_jsonld(html_text: str) -> tuple[list[dict], list[str]]:
    parser = JsonLdParser()
    parser.feed(html_text)
    found: list[dict] = []
    warnings: list[str] = []
    for i, block in enumerate(parser.blocks):
        if len(block.encode("utf-8")) > MAX_JSONLD_BYTES:
            warnings.append(f"JSONLD_TOO_LARGE:{i}")
            continue
        try:
            data = json.loads(block.strip())
        except (ValueError, TypeError):
            warnings.append(f"JSONLD_INVALID:{i}")
            continue
        for item in iter_nodes(data):
            if is_type(item, "Product"):
                found.append(item)
                if len(found) >= MAX_ITEMS:
                    warnings.append("PRODUCT_LIMIT_REACHED")
                    return found, warnings
    return found, warnings


def safe_https_url(url: object, *, danawa_only: bool = False) -> bool:
    if not isinstance(url, str) or len(url) > 2048:
        return False
    try:
        p = urlparse(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            return False
        host = p.hostname.rstrip(".").lower()
        if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
            return False
        if danawa_only and not (host == "danawa.com" or host.endswith(".danawa.com")):
            return False
        try:
            addr = ipaddress.ip_address(host)
            if not addr.is_global:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def krw_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip().replace(",", "")
    else:
        return None
    if not re.fullmatch(r"[0-9]+(?:\.0+)?", text):
        return None
    try:
        n = Decimal(text)
    except InvalidOperation:
        return None
    return int(n) if n == n.to_integral_value() and 0 < n < 10**12 else None


def aware_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo and dt.utcoffset() is not None else None


def safe_label(value: object) -> str:
    if isinstance(value, str):
        return value.strip()[:256]
    if isinstance(value, dict):
        return safe_label(value.get("name") or value.get("value"))
    return ""


def offer_candidates(products: list[dict]) -> tuple[list[dict], list[str]]:
    output: list[dict] = []
    warnings: list[str] = []
    for p in products:
        prod_name = safe_label(p.get("name"))
        model = safe_label(p.get("model") or p.get("sku") or p.get("mpn"))
        variant = safe_label(p.get("color") or p.get("size"))
        offered = p.get("offers", [])
        offered = offered if isinstance(offered, list) else [offered]
        for idx, offer in enumerate(offered):
            if not isinstance(offer, dict):
                warnings.append("OFFER_NOT_OBJECT")
                continue
            if is_type(offer, "AggregateOffer"):
                warnings.append("AGGREGATE_OFFER_SKIPPED")
                continue
            if not is_type(offer, "Offer"):
                warnings.append("UNSUPPORTED_OFFER_TYPE")
                continue
            price = offer.get("price")
            currency = offer.get("priceCurrency")
            if price is None and isinstance(offer.get("priceSpecification"), dict):
                spec = offer["priceSpecification"]
                price = spec.get("price")
                currency = currency or spec.get("priceCurrency")
            cond = safe_label(offer.get("itemCondition"))
            item_condition = "new" if cond.endswith("NewCondition") else "unknown"
            output.append({
                "name": prod_name,
                "candidate_model": model,
                "candidate_variant": variant,
                "price": krw_int(price),
                "currency": currency or "",
                "url": (str(offer.get("url") or p.get("url") or "").strip()),
                "condition": item_condition,
                "image_url": p.get("image", "") if isinstance(p.get("image"), str) else "",
                "offer_index": idx,
            })
            if len(output) >= MAX_ITEMS:
                warnings.append("OFFER_LIMIT_REACHED")
                return output, warnings
    return output, warnings


def inspect_snapshot(html_bytes: bytes, meta: dict, *, now: datetime | None = None,
                     demo: bool = False) -> dict:
    if len(html_bytes) > MAX_HTML_BYTES:
        raise ValueError("HTML_TOO_LARGE")
    if now is None:
        now = datetime.now(timezone.utc)
    html_text = html_bytes.decode("utf-8-sig", errors="replace")
    products, warnings = read_jsonld(html_text)
    candidates, extra_warnings = offer_candidates(products)
    warnings.extend(extra_warnings)
    capture_dt = aware_date(meta.get("observed_at"))
    source_url = meta.get("source_page", "")
    target = meta.get("target", {})
    target = target if isinstance(target, dict) else {}
    target_model = safe_label(target.get("model"))
    target_variant = safe_label(target.get("variant"))
    approved = meta.get("usage_permission") == "confirmed"
    payment_condition = str(meta.get("payment_condition", "unknown"))
    shipping_value = meta.get("shipping_fee")
    shipping = (0 if not isinstance(shipping_value, bool) and shipping_value == 0
                else krw_int(shipping_value))
    report_candidates = []
    export_rows = []
    for c in candidates:
        issues = []
        if demo:
            issues.append("DEMO_ONLY")
        if not approved:
            issues.append("SOURCE_PERMISSION_UNCONFIRMED")
        if not safe_https_url(source_url, danawa_only=True):
            issues.append("SOURCE_URL_INVALID_OR_NOT_DANAWA")
        if capture_dt is None:
            issues.append("OBSERVED_AT_MISSING_OR_NO_TIMEZONE")
        elif now - capture_dt > timedelta(hours=FRESH_HOURS) or capture_dt - now > timedelta(minutes=5):
            issues.append("OBSERVED_AT_OUTSIDE_24H")
        if c["price"] is None:
            issues.append("PRICE_INVALID")
        if c["currency"] != "KRW":
            issues.append("CURRENCY_NOT_KRW_OR_MISSING")
        if not safe_https_url(c["url"]):
            issues.append("OFFER_URL_INVALID")
        if not target_model or c["candidate_model"].lower() != target_model.lower():
            issues.append("MODEL_NOT_VERIFIED_EQUAL")
        if not target_variant or c["candidate_variant"].lower() != target_variant.lower():
            issues.append("VARIANT_NOT_VERIFIED_EQUAL")
        if c["condition"] != "new":
            issues.append("CONDITION_UNKNOWN_OR_NOT_NEW")
        if shipping is None:
            issues.append("SHIPPING_UNVERIFIED")
        if payment_condition != "normal":
            issues.append("PAYMENT_NOT_CONFIRMED_NORMAL")
        row = {
            "query": safe_label(target.get("query")),
            "model": target_model,
            "variant": target_variant,
            "candidate_model": c["candidate_model"],
            "candidate_variant": c["candidate_variant"],
            "base_price": c["price"] if c["price"] is not None else "",
            "shipping_fee": shipping if shipping is not None else "",
            "product_condition": c["condition"],
            "payment_condition": payment_condition,
            "url": c["url"],
            "observed_at": meta.get("observed_at", ""),
            "source_page": source_url,
            "image_path": "",
            "image_rights": "unknown",  # never download or assume permission
            "image_credit": "",
        }
        report_candidates.append({"product_name": c["name"], "price": c["price"],
                                  "url": c["url"], "model": c["candidate_model"],
                                  "variant": c["candidate_variant"], "issues": issues,
                                  "eligible_for_review_csv": not issues})
        if not issues:
            export_rows.append(row)
    status = ("DEMO_ONLY" if demo else "REVIEW_CANDIDATES_AVAILABLE" if export_rows
              else "NO_STRUCTURED_OFFERS" if not candidates else "HOLD_REVIEW")
    if not products:
        warnings.append("NO_JSONLD_PRODUCT_FOUND")
    return {
        "version": VERSION,
        "status": status,
        "notice": "로컬 HTML 구조 점검. 실시간 크롤링/전체 사이트 최저가 보증/발행 아님.",
        "snapshot_sha256": hashlib.sha256(html_bytes).hexdigest(),
        "snapshot_bytes": len(html_bytes),
        "checked_at_utc": now.astimezone(timezone.utc).isoformat(),
        "source_page_declared": source_url,
        "capture_time_declared": meta.get("observed_at"),
        "jsonld_product_count": len(products),
        "candidate_count": len(candidates),
        "review_csv_count": len(export_rows),
        "warnings": warnings,
        "candidates": report_candidates,
        "_csv_rows": export_rows,
    }


def render_html(report: dict) -> str:
    e = lambda t: html.escape(str(t if t is not None else ""), quote=True)
    lines = []
    for i, c in enumerate(report["candidates"], 1):
        issues = ", ".join(c["issues"]) or "사람의 최종 검토 필요"
        lines.append(f"<tr><td>{i}</td><td>{e(c['product_name'])}</td>"
                     f"<td>{e(c['model'])}</td><td>{e(c['variant'])}</td>"
                     f"<td>{e(c['price'])}</td><td>{e(issues)}</td></tr>")
    if not lines:
        lines.append("<tr><td colspan=6>구조화된 Product/Offer 가격 후보를 찾지 못했습니다.</td></tr>")
    warn = "<br>".join(e(x) for x in report["warnings"]) or "없음"
    return f"""<!doctype html><html lang="ko"><meta charset="utf-8">
<title>다나와 저장 HTML 구조 점검 — v{e(VERSION)}</title>
<style>body{{font:15px/1.65 'Malgun Gothic',sans-serif;background:#f5f7fa;color:#17263a;margin:0}}
main{{max-width:1080px;margin:36px auto;background:white;border-radius:18px;padding:28px;box-shadow:0 6px 30px #ccd2dc55}}
h1{{font-size:26px}}.badge{{background:#fdecc8;color:#6e4506;padding:8px 12px;border-radius:8px;font-weight:bold}}
table{{border-collapse:collapse;width:100%;margin:22px 0}}th,td{{border-bottom:1px solid #ddd;text-align:left;padding:10px;vertical-align:top}}
th{{background:#eaf4f8}}code{{overflow-wrap:anywhere}}small{{color:#526477}}</style>
<main><h1>다나와 HTML 저장본 구조 점검</h1><p><span class="badge">{e(report['status'])}</span></p>
<p>수집·발행 기능이 아닙니다. HTML 파일을 저장한 시각과 판매 가격의 실제 게시·유효 시각은 같지 않을 수 있습니다.</p>
<p><b>JSON-LD 상품:</b> {e(report['jsonld_product_count'])} · <b>Offer 후보:</b> {e(report['candidate_count'])} · <b>검토 CSV 후보:</b> {e(report['review_csv_count'])}</p>
<p><b>출처(사용자 입력):</b> <code>{e(report['source_page_declared'])}</code><br><b>확인시각(사용자 입력):</b> {e(report['capture_time_declared'])}</p>
<table><thead><tr><th>No.</th><th>상품명</th><th>모델</th><th>옵션</th><th>가격(KRW)</th><th>보류/검토 사유</th></tr></thead><tbody>{''.join(lines)}</tbody></table>
<h2>경고</h2><p>{warn}</p><small>SHA-256: <code>{e(report['snapshot_sha256'])}</code></small></main></html>"""


def save_report(report: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    export = report.copy()
    rows = export.pop("_csv_rows")
    json_file = output_dir / "snapshot_report.json"
    html_file = output_dir / "snapshot_report.html"
    csv_file = output_dir / "candidates_for_review.csv"
    json_file.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    html_file.write_text(render_html(report), encoding="utf-8")
    with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return {"json": str(json_file), "html": str(html_file), "csv": str(csv_file)}


def run(html_file: Path, meta_file: Path, output_dir: Path, *, demo=False) -> dict:
    if not html_file.is_file():
        raise ValueError(f"HTML_NOT_FOUND: {html_file}")
    if not meta_file.is_file():
        raise ValueError(f"META_NOT_FOUND: {meta_file}")
    if html_file.stat().st_size > MAX_HTML_BYTES:
        raise ValueError("HTML_TOO_LARGE")
    meta = json.loads(meta_file.read_text(encoding="utf-8-sig"))
    if not isinstance(meta, dict):
        raise ValueError("META_NOT_OBJECT")
    if demo:
        # Synthetic demo time is deliberately current, always prominently marked DEMO_ONLY.
        meta["observed_at"] = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
    report = inspect_snapshot(html_file.read_bytes(), meta, demo=demo)
    paths = save_report(report, output_dir)
    print(json.dumps({"status": report["status"], "candidates": report["candidate_count"],
                      "review_csv": report["review_csv_count"], "outputs": paths}, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description="Offline local-HTML price evidence probe. No web access.")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Inspect a user-saved local HTML file")
    inspect.add_argument("--html", type=Path, required=True)
    inspect.add_argument("--meta", type=Path, required=True)
    inspect.add_argument("--out", type=Path, default=Path("output/manual"))
    demo = sub.add_parser("demo", help="Synthetic demo only")
    demo.add_argument("--out", type=Path, default=Path("output/demo"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    try:
        if args.command == "demo":
            r = run(root / "fixtures" / "demo_product.html",
                    root / "fixtures" / "demo_meta.json", args.out, demo=True)
        else:
            r = run(args.html, args.meta, args.out)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        raise SystemExit(2)
    # Incomplete evidence is a review result, not an application crash.
    raise SystemExit(0 if r["status"] in ("REVIEW_CANDIDATES_AVAILABLE", "DEMO_ONLY", "HOLD_REVIEW", "NO_STRUCTURED_OFFERS") else 1)


if __name__ == "__main__":
    main()
