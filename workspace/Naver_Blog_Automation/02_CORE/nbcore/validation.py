from __future__ import annotations
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit
import ipaddress
import re

KST = timezone(timedelta(hours=9))
ALLOWED_RIGHTS = {"owned", "licensed", "permission"}

def now_kst() -> datetime:
    return datetime.now(KST)

def normalize_price(value: object) -> int | None:
    """Never concatenate different prices, installments or price ranges."""
    if type(value) is int:
        return value if value > 0 else None
    if not isinstance(value, str) or len(value)>80:
        return None
    m = re.fullmatch(r"\s*(?:₩\s*)?(\d{1,3}(?:,\d{3})+|\d+)\s*(?:원)?\s*", value)
    if not m:
        return None
    price = int(m.group(1).replace(",", ""))
    return price if price > 0 else None

def public_link(value: object) -> str | None:
    if not isinstance(value, str) or len(value)>2048 or any(ord(c)<32 for c in value):
        return None
    value=value.strip()
    try:
        p=urlsplit(value)
        host=p.hostname
        _=p.port
        if p.scheme not in {"https", "http"} or not host or p.username or p.password:
            return None
        if host in {"localhost"} or host.endswith((".local", ".localhost")) or "." not in host:
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        return value
    except ValueError:
        return None

def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result=datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except ValueError:
        return None

def normalize_records(records: object) -> list[dict]:
    if not isinstance(records,list) or not 1 <= len(records) <= 30:
        raise ValueError("상품 데이터 목록 1~30개가 필요합니다.")
    out=[]
    string_keys=("model", "variant", "image_path", "image_url", "image_rights", "image_credit", "image_source_page")
    for i, src in enumerate(records,1):
        if not isinstance(src,dict):
            raise ValueError(f"{i}행은 객체여야 합니다.")
        query=str(src.get("query","")).strip()
        if not 1 <= len(query) <= 200:
            raise ValueError(f"{i}행 상품명은 1~200자로 입력하세요.")
        r={"query":query}
        for key in string_keys:
            val=src.get(key) or ""
            if not isinstance(val,str) or len(val)>2048:
                raise ValueError(f"{i}행 {key} 값이 올바르지 않습니다.")
            r[key]=val.strip()
        r["input_issues"]=[]
        for source in ("danawa","naver"):
            raw=src.get(source+"_price")
            r[source+"_price"]=normalize_price(raw)
            if raw not in (None, "") and r[source+"_price"] is None:
                r["input_issues"].append(source+":INVALID_PRICE")
            r[source+"_url"]=public_link(src.get(source+"_url"))
            stamp=src.get(source+"_observed_at") or ""
            r[source+"_observed_at"]=stamp if isinstance(stamp,str) and len(stamp)<80 else ""
            r[source+"_match_checked"]=src.get(source+"_match_checked") is True
            r[source+"_terms_checked"]=src.get(source+"_terms_checked") is True
            r[source+"_condition"]=str(src.get(source+"_condition", "배송비·쿠폰 조건 미확인"))[:500]
        out.append(r)
    return out

def review_issues(record: dict, max_age_hours: int=24, now: datetime | None=None) -> list[str]:
    now=now or now_kst()
    issues=list(record.get("input_issues", []))
    if not record.get("model"):
        issues.append("MODEL_REQUIRED")
    for source in ("danawa", "naver"):
        if record.get(source+"_price") is None:
            issues.append(source+":PRICE_MISSING")
            continue
        if not public_link(record.get(source+"_url")):
            issues.append(source+":URL_INVALID")
        if not record.get(source+"_match_checked"):
            issues.append(source+":MATCH_NOT_REVIEWED")
        if not record.get(source+"_terms_checked"):
            issues.append(source+":TERMS_NOT_REVIEWED")
        elif not record.get(source+"_condition", "").strip():
            issues.append(source+":CONDITION_REQUIRED")
        stamp=parse_time(record.get(source+"_observed_at"))
        if stamp is None:
            issues.append(source+":TIMESTAMP_REQUIRED")
        elif (now-stamp).total_seconds() < -300:
            issues.append(source+":FUTURE_TIMESTAMP")
        elif (now-stamp).total_seconds() > max_age_hours*3600:
            issues.append(source+":STALE_PRICE")
    if record.get("image_rights") not in ALLOWED_RIGHTS:
        issues.append("IMAGE_RIGHTS_NOT_CONFIRMED")
    elif record.get("image_rights") in {"licensed", "permission"} and not record.get("image_credit", "").strip():
        issues.append("IMAGE_CREDIT_REQUIRED")
    return issues
