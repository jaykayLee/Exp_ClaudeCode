"""Direct adapter: Danawa snapshot probe report (v1.3.1) -> v1.0 panel input.

NEW CODE written in P01. It is NOT a reproduction of the missing
Naver_Blog_Danawa_Candidate_QA_Addon_v1.1 / CSV_Bridge_Addon_v1.2 (originals unavailable),
so compatibility with them is unverified: LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED.

Pure functions only: no file, network or publication side effects.
Result wording: "lowest among checked eligible candidates", never the absolute market lowest.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from nbcore.validation import parse_time, public_link

ADAPTER_ID = "SNAPSHOT_DIRECT_ADAPTER"
ADAPTER_VERSION = "0.1.0"
LEGACY_FLAG = "LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED"
SOURCE_KIND = "saved_html_snapshot"
# A user-saved snapshot can never be live_verified evidence.
SNAPSHOT_EVIDENCE_KINDS = {"synthetic", "user_recorded"}
PRICE_BASIS = "배송비 포함 일반 구매 총액 (상품가 + 확인된 배송비)"
PRICE_BASIS_CODE = "TOTAL_WITH_SHIPPING_NORMAL_PURCHASE"
FUTURE_TOLERANCE = timedelta(minutes=5)


def _label(value: object) -> str:
    return value.strip()[:256] if isinstance(value, str) else ""


def _pos_int(value: object) -> int | None:
    return value if type(value) is int and value > 0 else None


def _fee(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _product_id(source_page: str) -> str:
    try:
        values = parse_qs(urlsplit(source_page).query).get("pcode", [])
    except ValueError:
        return ""
    return values[0][:64] if len(values) == 1 and values[0].isalnum() else ""


def check_evidence_kind(evidence_kind: object, mode: str) -> str:
    if evidence_kind not in SNAPSHOT_EVIDENCE_KINDS:
        raise ValueError(f"EVIDENCE_KIND_NOT_ALLOWED_FOR_SNAPSHOT: {evidence_kind!r}")
    if mode not in {"DEMO", "MANUAL_IMPORT"}:
        raise ValueError("MODE_INVALID: DEMO / MANUAL_IMPORT")
    if evidence_kind == "synthetic" and mode != "DEMO":
        raise ValueError("SYNTHETIC_EVIDENCE_REQUIRES_DEMO_MODE")
    if evidence_kind != "synthetic" and mode == "DEMO":
        raise ValueError("DEMO_MODE_REQUIRES_SYNTHETIC_EVIDENCE")
    return evidence_kind


def normalize_snapshot_candidates(report: dict, per_offer_evidence: list | None = None, *,
                                  provider: str = "danawa", evidence_kind: str,
                                  collected_at: str, meta: dict | None = None) -> list[dict]:
    """Turn probe report candidates into the target candidate contract.

    Every field of one output dict comes from the SAME probe candidate (same offer):
    price, URL, seller, shipping, payment and observed_at are never mixed across offers.
    """
    if not isinstance(report, dict) or not isinstance(report.get("candidates"), list):
        raise ValueError("REPORT_INVALID")
    if evidence_kind not in SNAPSHOT_EVIDENCE_KINDS:
        raise ValueError(f"EVIDENCE_KIND_NOT_ALLOWED_FOR_SNAPSHOT: {evidence_kind!r}")
    meta = meta if isinstance(meta, dict) else {}
    notes: dict = {}
    for entry in per_offer_evidence or []:
        if isinstance(entry, dict) and isinstance(entry.get("url"), str):
            notes.setdefault(entry["url"].strip(), []).append(_label(entry.get("evidence")))
    digest = str(report.get("snapshot_sha256") or "")
    source_page = str(report.get("source_page_declared") or "")
    observed_at = report.get("capture_time_declared")
    observed_at = observed_at if isinstance(observed_at, str) else ""
    out = []
    for position, c in enumerate(report["candidates"]):
        if not isinstance(c, dict):
            raise ValueError("REPORT_CANDIDATE_INVALID")
        index = c.get("offer_index", position)
        issues = [str(x) for x in c.get("issues", []) if isinstance(x, str)]
        url = _label(c.get("url")) if isinstance(c.get("url"), str) else ""
        base = _pos_int(c.get("price"))
        ship = _fee(c.get("shipping_fee"))
        out.append({
            "provider": provider,
            "source_kind": SOURCE_KIND,
            "evidence_kind": evidence_kind,
            "product_id": _product_id(source_page),
            "candidate_id": f"{digest[:12] or 'nohash'}:{index}",
            "seller_id": _label(c.get("seller_id")),
            "seller_name": _label(c.get("seller_name")),
            "model": _label(c.get("model")),
            "variant": _label(c.get("variant")),
            "base_price": base,
            "shipping_fee": ship,
            "total_price": base + ship if base is not None and ship is not None else None,
            "currency": _label(c.get("currency")),
            "product_condition": _label(c.get("product_condition")) or "unknown",
            "payment_condition": _label(c.get("payment_condition")) or "unknown",
            "shipping_source": _label(c.get("shipping_source")) or "none",
            "payment_source": _label(c.get("payment_source")) or "none",
            "url": url,
            "source_page": source_page,
            "observed_at": observed_at,
            "collected_at": collected_at,
            "snapshot_sha256": digest,
            "permission_reference": _label(meta.get("permission_reference")) or
                                    ("usage_permission=" + _label(meta.get("usage_permission") or "unknown")),
            "match_status": ("UNVERIFIED" if {"MODEL_NOT_VERIFIED_EQUAL", "VARIANT_NOT_VERIFIED_EQUAL"} & set(issues)
                             else "EXACT"),
            "review_issues": issues,
            "terms_evidence": [n for n in notes.get(url, []) if n],
        })
    return out


def evaluate_candidates(target: dict, candidates: list[dict], *, now: datetime,
                        max_age_hours: int = 24, demo: bool = False) -> list[dict]:
    """Independent re-check (defence in depth). Adds `eligible` and `exclusion_reasons`.

    In DEMO, the probe's DEMO_ONLY flag is kept on the candidate as a label, but it does not
    exclude synthetic candidates from the selection exercise. Outside DEMO it excludes.
    """
    if now.tzinfo is None:
        raise ValueError("NOW_REQUIRES_TIMEZONE")
    if type(max_age_hours) is not int or not 1 <= max_age_hours <= 168:
        raise ValueError("MAX_AGE_HOURS_INVALID")
    t_model = _label(target.get("model")).lower()
    t_variant = _label(target.get("variant")).lower()
    evaluated = []
    for c in candidates:
        reasons = [x for x in c.get("review_issues", []) if not (demo and x == "DEMO_ONLY")]
        def add(code: str) -> None:
            if code not in reasons:
                reasons.append(code)
        if demo and c.get("evidence_kind") != "synthetic":
            add("DEMO_REQUIRES_SYNTHETIC")
        base, ship = _pos_int(c.get("base_price")), _fee(c.get("shipping_fee"))
        if base is None:
            add("PRICE_INVALID")
        if ship is None:
            add("SHIPPING_UNVERIFIED")
        if base is None or ship is None or type(c.get("total_price")) is not int or c["total_price"] != base + ship:
            add("TOTAL_NOT_COMPUTABLE")
        if c.get("currency") != "KRW":
            add("CURRENCY_NOT_KRW_OR_MISSING")
        if c.get("product_condition") != "new":
            add("CONDITION_UNKNOWN_OR_NOT_NEW")
        if c.get("payment_condition") != "normal":
            add("PAYMENT_NOT_CONFIRMED_NORMAL")
        url = c.get("url") or ""
        if not public_link(url) or urlsplit(url).scheme != "https":
            add("OFFER_URL_INVALID")
        if not t_model or (c.get("model") or "").lower() != t_model:
            add("MODEL_NOT_VERIFIED_EQUAL")
        if not t_variant or (c.get("variant") or "").lower() != t_variant:
            add("VARIANT_NOT_VERIFIED_EQUAL")
        stamp = parse_time(c.get("observed_at"))
        if stamp is None:
            add("OBSERVED_AT_MISSING_OR_NO_TIMEZONE")
        elif stamp - now > FUTURE_TOLERANCE:
            add("OBSERVED_AT_FUTURE")
        elif now - stamp > timedelta(hours=max_age_hours):
            add("OBSERVED_AT_STALE")
        evaluated.append({**c, "eligible": not reasons, "exclusion_reasons": reasons})
    return evaluated


def select_lowest_eligible(candidates: list[dict]) -> dict:
    """Lowest total among eligible candidates; deterministic tie-break by candidate_id."""
    eligible = [c for c in candidates if c.get("eligible") is True]
    ranked = sorted(eligible, key=lambda c: (c["total_price"], c["base_price"], c["candidate_id"]))
    excluded = [{"candidate_id": c.get("candidate_id"), "url": c.get("url"),
                 "reasons": c.get("exclusion_reasons", [])} for c in candidates if c.get("eligible") is not True]
    if not ranked:
        return {"status": "NO_ELIGIBLE_CANDIDATE" if candidates else "NO_CANDIDATE", "selected": None, "ranking": [], "ties": [],
                "excluded": excluded, "basis": PRICE_BASIS, "basis_code": PRICE_BASIS_CODE}
    best = ranked[0]
    ties = [c["candidate_id"] for c in ranked[1:] if c["total_price"] == best["total_price"]]
    return {"status": "SELECTED", "selected": best,
            "ranking": [{"candidate_id": c["candidate_id"], "total_price": c["total_price"],
                         "url": c["url"]} for c in ranked],
            "ties": ties, "excluded": excluded, "basis": PRICE_BASIS, "basis_code": PRICE_BASIS_CODE}


def _won(n: int) -> str:
    return f"{n:,}원"


def to_panel_input(target: dict, selection: dict, *, evidence_kind: str, source: str = "danawa") -> dict:
    """Build one v1.0 record (product_input.schema.json). Human-review flags stay False."""
    if source != "danawa":
        raise ValueError("SOURCE_NOT_SUPPORTED_BY_SNAPSHOT_ADAPTER")
    query = _label(target.get("query"))
    if not query:
        raise ValueError("TARGET_QUERY_REQUIRED")
    record = {"query": query, "model": _label(target.get("model")), "variant": _label(target.get("variant"))}
    for key in ("image_path", "image_url", "image_rights", "image_credit", "image_source_page"):
        if isinstance(target.get(key), str):
            record[key] = target[key]
    demo_tag = "[합성 DEMO] " if evidence_kind == "synthetic" else ""
    chosen = selection.get("selected") if isinstance(selection, dict) else None
    if chosen:
        seller = chosen.get("seller_name") or chosen.get("seller_id") or "판매자명 미기재"
        condition = (f"{demo_tag}{PRICE_BASIS}: 상품가 {_won(chosen['base_price'])} + 배송비 "
                     f"{_won(chosen['shipping_fee'])} = {_won(chosen['total_price'])} / 판매자 {seller} / "
                     f"근거 {SOURCE_KIND}·{evidence_kind}·sha256 {chosen['snapshot_sha256'][:12]} / "
                     "확인한 적합 후보 내 최저가이며 전체 시장 최저가 보장 아님")
        record.update({f"{source}_price": chosen["total_price"], f"{source}_url": chosen["url"],
                       f"{source}_observed_at": chosen["observed_at"]})
    else:
        reasons = sorted({r for e in (selection or {}).get("excluded", []) for r in e.get("reasons", [])})
        condition = f"{demo_tag}적합 후보 없음 (보류): " + (", ".join(reasons)[:400] or "후보 없음")
        record.update({f"{source}_price": None, f"{source}_url": None, f"{source}_observed_at": ""})
    record.update({f"{source}_match_checked": False, f"{source}_terms_checked": False,
                   f"{source}_condition": condition[:500]})
    # Naver source is not connected yet (P03). Keep explicit 미수집, never 0원.
    record.update({"naver_price": None, "naver_url": None, "naver_observed_at": "",
                   "naver_match_checked": False, "naver_terms_checked": False,
                   "naver_condition": "네이버쇼핑 미수집 — 허용된 데이터 경로 미연결 (P03 이전)"})
    return record
