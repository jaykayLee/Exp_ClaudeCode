---
name: danawa-snapshot-onboarding
description: Onboard a real Danawa product page that the user saved in their own browser (P08 / P02 option A) — write meta and job files, run the offline probe and bridge, document the real JSON-LD/seller structure, and turn it into an anonymized regression fixture. Use when the user uploads a saved Danawa .html/.mhtml, asks to "실제 다나와 페이지 점검", or wants to create 07_DATA/inbox/snapshot_job.json.
---

# Danawa saved-snapshot onboarding (offline only)

No network requests to Danawa. The user saves the page; we only read the file.

## Inputs to ask for (one message, all at once)
1. The saved HTML file (Ctrl+S "웹페이지, 전체" or HTML only).
2. When it was viewed: `YYYY-MM-DDTHH:MM:SS+09:00`.
3. Exact model and option (color/capacity) to compare.
4. Per seller URL they checked: payment condition (`normal` / `card_only` / `rental` / `coupon` / `unknown`) and shipping fee if confirmed.
5. Whether they confirmed the site's terms allow this use (`usage_permission`: `confirmed` / `unknown`) — never assume.

## Steps
1. Copy files into `workspace/Naver_Blog_Automation/07_DATA/inbox/` (never commit real user files there; that folder is git-ignored).
2. Write `*_meta.json` from `11_ADDONS/DANAWA_SNAPSHOT_PROBE/fixtures/manual_meta_template.json`: `target`, `source_page`, `observed_at`, `usage_permission`, `offer_terms[]` (URL must equal the JSON-LD offer url exactly). Do not set `offer_terms_scope: "all_offers"` unless the user confirmed the same terms for every seller.
3. Write `snapshot_job.json` (`schema_version: snapshot_job.1`, `mode: MANUAL_IMPORT`, `evidence_kind: user_recorded`, no `evaluation_time`).
4. Structure probe first: `python -m probe.snapshot_probe inspect --html … --meta … --out <tmp>` from the add-on folder; read `snapshot_report.json` warnings (`NO_JSONLD_PRODUCT_FOUND`, `AGGREGATE_OFFER_SKIPPED`, …).
5. Record findings in `docs/DANAWA_REAL_STRUCTURE.md`: where Product/Offer/seller/shipping appear, what is missing, whether prices are AggregateOffer only. Do not invent CSS selectors or private API URLs; if the data is not in structured markup, record `BLOCKED_EXTERNAL`/HOLD instead of scraping text.
6. Run the bridge: `.venv/bin/python tools/run_snapshot_to_panel.py --job 07_DATA/inbox/snapshot_job.json` → expect HOLD until a person ticks review flags.
7. Regression fixture: copy only the JSON-LD block (strip cookies, user names, tracking params, ads) into `07_DATA/samples/real_structure/` with a note "구조 보존·값 익명화"; add tests in `10_TESTS/` that pin the parsed structure. Follow `price-data-contract`.

## Report
Structure found, candidates and exclusion reasons, selected total (or none), what remains unknown. Live collection stays `BLOCKED_EXTERNAL` unless an allowed source is confirmed.
