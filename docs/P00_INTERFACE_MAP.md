# P00 — 실제 인터페이스 매핑과 P01 확정 범위

- 작성일: 2026-11-05 / 근거: 이 세션에서 실제로 읽은 코드 + `00_SESSION/evidence/p00_interface_probe.{py,json,txt}` 실행 결과
- 실행 환경: Linux x86_64 (클라우드 컨테이너), Python 3.13.18, venv + Pillow 12.3.0 (lock 일치)
- 이 문서는 **설계 확정**이다. P01 구현은 아직 하지 않았다.

## 1. 실제 호출 가능한 함수 (시그니처는 `inspect.signature`로 추출)

### v1.0 Core (`workspace/Naver_Blog_Automation`)

| 위치 | 함수 | 입력 | 출력 / 비고 |
|---|---|---|---|
| `02_CORE/nbcore/validation.py` | `normalize_records(records)` | list[dict] 1~30개. 키: `query`(필수), `model`, `variant`, `image_*`, `{danawa,naver}_{price,url,observed_at,match_checked,terms_checked,condition}` | 정규화 dict 목록. **그 외 키는 버린다** (probe: `source_kind`, `snapshot_sha256`, `evidence_kind`, `candidate_id`, `shipping_fee` 소실 확인) |
| 〃 | `review_issues(record, max_age_hours=24, now=None)` | 정규화 행 | `source:CODE` 이슈 목록 (PRICE_MISSING, URL_INVALID, MATCH_NOT_REVIEWED, TERMS_NOT_REVIEWED, TIMESTAMP_REQUIRED, STALE_PRICE, FUTURE_TIMESTAMP …) |
| 〃 | `normalize_price(value) -> int\|None` | int 또는 단일 금액 문자열 | bool·0·음수·범위·할부 → None |
| 〃 | `public_link(value) -> str\|None` | URL | http/https 공개 호스트만 |
| `02_CORE/nbcore/pipeline.py` | `run_pipeline(root, records, mode="MANUAL_IMPORT")` | mode ∈ {DEMO, MANUAL_IMPORT} | `08_OUTPUT/runs/<id>/` 에 `product_table.html`, `normalized_products.json`, `run_report.json`, `NAVER_HANDOFF.md`, `images/`. gate = DEMO_ONLY / HOLD / READY_FOR_MANUAL_REVIEW. `pipeline.lock`으로 중복 실행 차단 |
| `02_CORE/exporters/table_exporter.py` | `render_product_table(products, image_base_dir=None, title=...)` | `query, image_path, danawa_price, danawa_url, naver_price, naver_url` | **7열 헤더 정확히 일치 확인** (`HEADERS`). 가격은 int>0만 표시, 나머지 "미수집" |
| `03_PROVIDERS/providers/base.py` | `PriceCandidate` (dataclass), `PriceProvider.collect(model, variant)` | — | 필드: provider, product_id, model, variant, price, url, observed_at, price_basis, image_url. **배송비·판매자·결제조건·증거 필드 없음** |
| `03_PROVIDERS/providers/danawa.py`, `naver_shopping.py` | `collect()` | — | 항상 `ProviderUnavailable` (의도된 미구현) |
| `03_PROVIDERS/providers/approved_import.py` | `load_approved_input(path)` | JSON ≤2MiB | `normalize_records` 결과 |
| `tools/run_once.py` | CLI `--demo` | `07_DATA/inbox/products.json` (기본 `records: []` → exit 1) | run_report JSON 출력 |

### v1.3 Snapshot Probe (`11_ADDONS/DANAWA_SNAPSHOT_PROBE`)

| 함수 | 입력 | 출력 / 비고 |
|---|---|---|
| `inspect_snapshot(html_bytes, meta, *, now=None, demo=False)` | 저장 HTML 바이트 + meta(`target{query,model,variant}`, `source_page`, `observed_at`, `usage_permission`, `shipping_fee`, `payment_condition`) | report dict: `status`, `snapshot_sha256`, `candidates[]`(product_name, price, url, model, variant, issues, eligible_for_review_csv), `_csv_rows[]` |
| `offer_candidates(products)` | JSON-LD Product 목록 | 후보 키: name, candidate_model, candidate_variant, price, currency, url, condition, image_url, offer_index. **seller·shippingDetails·결제조건을 읽지 않음** |
| `save_report(report, output_dir)` | — | `snapshot_report.json/html`, `candidates_for_review.csv` (CSV_COLUMNS 15개) |
| `run(html_file, meta_file, output_dir, *, demo=False)` | — | demo=True면 **observed_at을 현재 시각으로 덮어씀** → P01 하네스는 `inspect_snapshot(now=고정값)`을 직접 호출해야 함 |

## 2. 확인된 결함 / 불일치 (probe로 재현)

| ID | 내용 | 증거 |
|---|---|---|
| I02 | `inspect_snapshot`이 meta의 `shipping_fee`·`payment_condition`을 **모든 Offer에 공통 적용**. A=119000(무료), B=117000(+5000), C=80000(카드 전용)을 넣고 meta shipping=0/normal이면 3개 모두 적격, 단순 최저가는 **C(카드 전용)**로 오선택 | probe `I02_meta_shipping_applied_to_all_offers` |
| I02b | Offer 단위 `seller`, `shippingDetails`가 후보에 남지 않음 → 후보별 근거 연결 불가 | `I02_offer_level_seller_shipping_dropped` |
| I03 | v1.3 CSV 열(`base_price, shipping_fee, url, observed_at, source_page, …`)과 v1.0 입력 키(`danawa_price, danawa_url, danawa_observed_at, danawa_*_checked, danawa_condition`)가 다름. v1.3 행을 그대로 넣으면 **가격·URL·시각이 모두 소실** | `I03_schema_mismatch`, `I03_direct_feed_loses_price` |
| I08 | v1.0 `normalize_records`가 추가 증거 필드를 버림 → evidence sidecar 필수 | `evidence_fields_dropped_by_normalize_records` |
| I09 | 신선도 기준 이원화: v1.3 `FRESH_HOURS=24` 하드코딩 vs v1.0 설정 `max_price_age_hours`(1~168) | `freshness_threshold_split` |
| I10 | v1.3 `run(demo=True)`가 observed_at을 현재 시각으로 교체 (DEMO 표식은 유지되나 "관측시각 보존" 원칙과 충돌) | `v1_3_run_demo_overwrites_observed_at` |
| I11 | `07_DATA/inbox/products.json` 기본값 `records: []` → `run_once.bat`(비데모)는 입력 전까지 exit 1 | `v1_0_empty_inbox_rejected` |
| — | v1.1/v1.2 원본 없음. v1.3 manifest의 `optional_integration`에 이름만 존재, CSV는 "v1.2-shaped"라고 주장하지만 **검증 불가** | SOURCE_INVENTORY.json |

정상 확인: 7열 헤더, DEMO 시 v1.3 CSV 0건(안전 계약), v1.0 DEMO 파이프라인 격리 실행 시 gate=DEMO_ONLY·7열·네트워크 수집 false·게시 false.

## 3. P01 접합 설계 (확정)

```
저장 HTML + meta(+per-offer 근거)
   └─ [수정] v1.3 inspect_snapshot  : 후보별 seller/shipping/payment + 근거 출처 필드 보존
        └─ [신규] providers/snapshot_adapter.py
             normalize_snapshot_candidates(report, per_offer_evidence)
             evaluate_candidates(target, candidates, *, now, max_age_hours)
             select_lowest_eligible(candidates)          # 배송비 포함 일반구매 총액 기준
             to_panel_input(target, selection, *, evidence_kind) -> v1.0 record (danawa_* 키)
        └─ [신규] tools/run_snapshot_to_panel.py  run_snapshot_to_panel(input_paths, output_dir)
             ├─ v1.0 run_pipeline(root, records, mode)  (기존 인터페이스 그대로)
             └─ evidence_sidecar.json + 실행 보고 (normalize_records가 버리는 근거 보존)
```

### 수정·신규 파일 (정확한 목록)

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| 수정 | `11_ADDONS/DANAWA_SNAPSHOT_PROBE/probe/snapshot_probe.py` | `offer_candidates`: offer별 `seller`, `shippingDetails.shippingRate`(KRW 정수/0 명시만), 결제 조건 근거 필드 추가(가산적). `inspect_snapshot`: offer 값 우선, meta 값은 `meta["offer_terms_scope"] == "all_offers"`일 때만 전 후보 적용. 그 외는 `SHIPPING_UNVERIFIED`/`PAYMENT_NOT_CONFIRMED_NORMAL`. 각 후보에 `shipping_source`, `payment_source`(offer/meta_all_offers/none), `offer_index`를 report에 노출. `FRESH_HOURS`는 인자로 받을 수 있게(기본 24 유지) |
| 수정 | `11_ADDONS/DANAWA_SNAPSHOT_PROBE/tests/test_snapshot_probe.py` | 기존 19개 유지. `BASE` meta에 `offer_terms_scope:"all_offers"` 1줄 추가(의도적 계약 변경, DECISIONS 기록). 신규: scope 없는 meta 배송비 → 보류, A/B/C 회귀 |
| 신규 | `03_PROVIDERS/providers/snapshot_adapter.py` | 위 4개 함수. 후보 계약 필드(provider, source_kind, evidence_kind, candidate_id, seller_id, base_price, shipping_fee, total_price, currency, product_condition, payment_condition, url, source_page, observed_at, collected_at, snapshot_sha256, match_status, review_issues). **신규 코드이며 v1.1/v1.2 재현이 아님** (`LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED`) |
| 신규 | `tools/run_snapshot_to_panel.py` | 단일 실행 진입점. 결과 폴더에 `evidence_sidecar.json` |
| 신규 | `10_TESTS/test_snapshot_bridge.py` | 합성 1상품/후보 3개 E2E(DEMO 하네스), §7 인수 항목 |
| 변경 없음 | `nbcore/validation.py`, `pipeline.py`, `table_exporter.py`, `PriceCandidate` | 어댑터로만 연결. 외부 인터페이스 유지 |

### P01 인수 기준 (P01 시작 시 그대로 사용)
1. 기존 31 + 19 테스트 회귀 PASS (BASE 1줄 변경은 기록과 함께).
2. A/B/C: A(119000+0=119000) 선택, B(122000) 후순위, C(카드 전용) 제외.
3. 미확인 배송비·옵션 불일치·중고·시각 누락·24h 초과·잘못된 URL → 사유와 함께 제외.
4. 선택 후보의 가격·URL·observed_at이 같은 offer에서 나옴 (A 가격 + B URL 금지).
5. v1.0 `danawa_price`에는 총액(int)만, `danawa_condition`에 "배송비 포함 일반 구매 총액 (상품가 X + 배송비 Y)" 기록. 7열 불변, 기준은 표 하단 문구.
6. DEMO 하네스: `evidence_kind=synthetic` 전 구간 유지, 최종 `mode=DEMO`/`DEMO_ONLY`. v1.3 DEMO CSV 비어 있음 계약 유지.
7. observed_at 재출력 시 원래 값 유지. 네이버 열은 미수집(None) 상태로 행 유지.
8. `*_match_checked`/`*_terms_checked`는 **사람 확인 플래그**이므로 어댑터가 자동으로 true로 만들지 않는다 → MANUAL_IMPORT라도 gate=HOLD가 정상. (자동 검증 결과는 sidecar의 `match_status`/`review_issues`에 기록)

## 4. 미검증 (이번 세션에서 수행하지 않음)
- Windows BAT 설치·실행: **NOT_RUN** (Linux 성공 ≠ Windows 성공)
- 실제 다나와 페이지/HTML 구조, 이용 조건: **NOT_RUN / BLOCKED_EXTERNAL**
- 네이버쇼핑 대체 경로: **NOT_RUN / BLOCKED_EXTERNAL** (2026-07-31 API 종료 공지는 인계 문서 기준이며 이번 세션에서 재확인하지 않음 → P03 시작 시 재확인)
- 네이버 블로그 게시: **NOT_IMPLEMENTED** (`auto_publish=false` 유지)
- v1.0↔v1.3 E2E: **NOT_RUN** (P01 범위)
