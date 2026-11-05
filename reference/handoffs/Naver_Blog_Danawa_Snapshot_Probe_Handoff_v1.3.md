# Naver Blog Automation — v1.3 Add-on Handoff

**Date:** 2026-11-01. **Project baseline:** v1.0 workspace + v1.1 Danawa Candidate QA + v1.2 CSV Bridge (as described in preceding handoff). **This release:** `DANAWA_SNAPSHOT_PROBE` v1.3.

This release does NOT claim to have implemented live Danawa crawling, Naver Shopping search API, image copyright clearance, or automated blog publishing. Prior ZIP files could not be downloaded in this runtime; neither actual Windows integration nor compatibility with the real v1.2 code is verified.

## Fixed user requirements
- Windows double-click BAT install/run/doctor/smoke.
- Exact final table columns: `No. | 상품명 | 이미지 | 다나와 최저가 | 사이트 주소 | 네이버 최저가 | 사이트 주소`.
- Core/Providers/Content/Publishers separated; new platform expansion via adapters.
- Preserve original images and 354×472px 300dpi optional conversion settings in v1.0, do not alter image code here.
- Missing site source stays `미수집`, never fabricate zero or price.

## Delta
- New isolated local HTML evidence probe in `11_ADDONS/DANAWA_SNAPSHOT_PROBE`.
- Extract JSON-LD `Product` -> `Offer` only, skip `AggregateOffer.lowPrice`, never guess from arbitrary page text.
- Strict user-declared metadata: model, variant, shipping, payment, captured_at timezone, usage rights assertion.
- Output: `snapshot_report.json`, `.html`, `candidates_for_review.csv` with v1.2-described input columns. Eligible rows still manual review, never automatic publication.
- SHA256 of HTML input in report; stale >24h HOLD; model/variant mismatch HOLD; demo always DEMO_ONLY.
- No outbound HTTP requests, no credentials, no browser automation.

## Actual verification
- Python standard-library unittest 19 tests passed in this build runtime; synthetic HTML only.
- Real Danawa HTML and Windows BAT runtime not tested.
- Prior v1.0/v1.1/v1.2 binaries unavailable for active integration regression; do not claim integration PASS.

## Next step
User Windows: execute `doctor.bat`, `smoke.bat`, `run_demo.bat` then save ONE real permitted Danawa product HTML snapshot; run local probe; share `snapshot_report.json` and (if allowed) redacted HTML. If no JSON-LD, stop heuristic parser; use approved data feed/manual CSV as fallback. Before distribution/publication, confirm appropriate data-use permissions. Source status is top blocker. Then verify CSV Bridge v1.2 and build only a targeted approved feed adapter.
