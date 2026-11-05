---
name: price-data-contract
description: Mandatory rules for any code or data that touches price candidates, shipping/payment terms, URLs, observed_at timestamps, evidence_kind/DEMO labels, images or the 7-column comparison table in the Naver Blog automation project. Use before editing snapshot_probe, snapshot_adapter, run_snapshot_to_panel, pipeline inputs, exporters or fixtures, and when reviewing such changes.
---

# Price data contract (do not break)

## 7-column table
Headers exactly, in order: `No. | 상품명 | 이미지 | 다나와 최저가 | 사이트 주소 | 네이버 최저가 | 사이트 주소`. Never add an 8th column; extra info goes below the table or in `bridge/evidence_sidecar.json`. Internal keys stay `danawa_url` / `naver_url`.

## Prices
- Positive `int` or `None`. Reject bool, 0, ranges, monthly/installment, mixed strings. Missing is `None` → shown "미수집", never 0원.
- Comparison basis = shipping-inclusive normal-purchase total. `total = base + shipping` only when both are confirmed.
- Shipping `0` only when free shipping is confirmed for THAT offer; unknown is `None`.
- Meta-level shipping/payment apply to all offers only with `offer_terms_scope: "all_offers"`.
- Card-only / rental / contract / coupon / installment wording → excluded (`PAYMENT_CONDITIONAL_HINT`), even if a record says normal.
- Price, URL, seller, shipping, payment and observed_at of a selected row must come from the SAME offer.
- Wording: "확인한 적합 후보 내 최저가" — never "전체 시장 최저가".

## Time
- `observed_at` = real observation time with timezone. Never replace it with processing/export time. Missing tz, future (>5 min), or older than `quality.max_price_age_hours` → excluded with a reason.
- Fixed evaluation clocks are allowed only in DEMO jobs (`evaluation_time`).

## Evidence & modes
- `evidence_kind`: `synthetic` (DEMO only) / `user_recorded` (MANUAL_IMPORT) / `live_verified` (never from a saved snapshot).
- DEMO keeps `DEMO_ONLY` to the final HTML/JSON; the v1.3 DEMO CSV stays empty.
- Human review flags `*_match_checked` / `*_terms_checked` are set only by a person in the panel — code must not set them True.
- One source failing must not erase other rows/sources; show HOLD / 미수집, never hide.

## Images
Keep originals byte-identical (hash-named); output 354×472 @300dpi white padding, aspect kept; a broken image keeps the price row. Rights are a user declaration, not software verification.

## External
No live scraping, login, CAPTCHA/403/429 bypass, proxy rotation, paid API, auto-publish, or schedule registration without explicit user approval. Naver Shopping legacy search API is retired — do not implement it. No secrets in code, logs, HTML or ZIPs.

## Checklist before commit
- [ ] Tests for every new exclusion reason and for "same offer" binding
- [ ] `tools/qa_runner.py` green
- [ ] No 8th column, no 0원 for missing, DEMO label preserved
