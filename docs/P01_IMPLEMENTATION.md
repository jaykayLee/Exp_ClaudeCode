# P01 — Snapshot → 후보별 검증 → v1.0 입력 → 7열 표 (구현 기록)

- 작성일: 2026-11-05 / 기준: `docs/P00_INTERFACE_MAP.md` §3
- 범위: 합성(DEMO) 및 사용자 기록 스냅샷의 오프라인 연결. **실시간 수집·Windows·게시는 포함하지 않는다.**

## 1. 데이터 흐름

```
job.json ─┬─ product_x.html (사용자가 저장한 페이지 / 합성)
          └─ product_x_meta.json (target, source_page, observed_at, usage_permission, offer_terms[...])
   │
   ▼ tools/run_snapshot_to_panel.py  (단일 진입점)
   ├─ probe.snapshot_probe.inspect_snapshot()   v1.3.1: 후보별 배송비·결제조건·판매자
   ├─ providers.snapshot_adapter
   │    normalize_snapshot_candidates → evaluate_candidates(독립 재검증) → select_lowest_eligible → to_panel_input
   ├─ nbcore.pipeline.run_pipeline()            v1.0 그대로 (7열 표, 이미지, HOLD/DEMO 게이트)
   └─ <run>/bridge/evidence_sidecar.json + product_NN_probe/  (v1.0 정규화가 버리는 근거 보존)
```

## 2. 바꾼 파일

| 구분 | 파일 | 내용 |
|---|---|---|
| 수정 | `11_ADDONS/DANAWA_SNAPSHOT_PROBE/probe/snapshot_probe.py` | v1.3.1. 후보별 조건 판단. 상세는 애드온 `docs/CHANGELOG_1.3.1.md` |
| 수정 | `11_ADDONS/.../tests/test_snapshot_probe.py` | `BASE`에 scope 1줄(의도적 계약 변경), 신규 7개 |
| 수정 | `11_ADDONS/.../addon_manifest.json`, `fixtures/manual_meta_template.json`, `SHA256SUMS.txt` | 버전·템플릿(offer_terms 예시)·체크섬 |
| 신규 | `03_PROVIDERS/providers/snapshot_adapter.py` | 직접 어댑터 (**v1.1/v1.2 아님**, `LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED`) |
| 신규 | `tools/run_snapshot_to_panel.py` | 단일 실행 진입점 `run_snapshot_to_panel(input_paths, root)` |
| 신규 | `07_DATA/samples/snapshot_demo/*` | 합성 job·HTML·meta 3상품 |
| 신규 | `10_TESTS/test_snapshot_bridge.py` | P01 인수 테스트 19개 (`qa_runner.py`가 자동 포함) |
| 변경 없음 | `nbcore/*`, `exporters/*`, `providers/base.py`, `06_UI`, BAT 전부 | v1.0 외부 인터페이스 유지 |

> 마스터 프롬프트의 예시 시그니처 `run_snapshot_to_panel(input_paths, output_dir)`는 v1.0 pipeline이 `root/08_OUTPUT/runs/<id>`에 쓰는 기존 구조를 유지하기 위해 `(input_paths, root)`로 구현했다. 산출물은 그 run 폴더 안 `bridge/`에 생긴다.

## 3. 판단 규칙 (요약)

- **배송비**: Offer별 근거만 사용한다(사용자 `offer_terms` URL 기록 > JSON-LD `shippingDetails`, 둘이 다르면 보류). 공통 meta 값은 `offer_terms_scope: "all_offers"`를 명시할 때만 적용한다. 0원은 명시적으로 확인된 경우만이고, 미확인은 None이다.
- **결제조건**: `offer_terms`의 `payment_condition` == `normal`일 때만 일반 구매로 본다. 카드·렌탈·약정·쿠폰·할부 문구가 Offer에 있으면 보류한다.
- **가격 비교 기준**: 배송비 포함 일반 구매 총액. 총액이 같으면 상품가가 낮은 쪽, 그다음 candidate_id 순서로 결정한다. 동률은 `ties`에 기록한다.
- **v1.0 입력**: `danawa_price` = 총액 int. `danawa_url`·`danawa_observed_at`은 **같은 Offer**에서 가져온다. `danawa_condition`에 "상품가 + 배송비 = 총액 / 판매자 / 근거 / 전체 시장 최저가 보장 아님"을 쓴다.
- **사람 확인 플래그** `danawa_match_checked/terms_checked`는 항상 False다. 그래서 MANUAL_IMPORT 결과는 HOLD가 정상이다. 자동 검사 결과는 sidecar의 `match_status`·`exclusion_reasons`에 있다.
- **네이버 열**: P03 이전이므로 `None`(표시 "미수집")이다. 0원으로 표시하지 않는다.
- **DEMO**: evidence_kind=`synthetic`만 허용한다. v1.3을 demo=True로 호출해 v1.3 CSV 0건 계약을 유지한다. DEMO_ONLY는 후보 라벨로 남기고 선택 연습에서만 제외 사유로 보지 않는다. 최종 pipeline mode=DEMO → gate DEMO_ONLY. 합성 데이터의 고정 평가시각(`evaluation_time`)은 DEMO job에서만 허용한다.
- **MANUAL_IMPORT**: evidence_kind=`user_recorded`만 허용하고 실제 시계를 쓴다. `live_verified`는 스냅샷 경로에서 거부한다.
- **부분 실패**: 스냅샷·meta 누락, 경로 이탈, job↔meta 대상 불일치가 생겨도 해당 행은 `SNAPSHOT_FAILED`로 유지하고 다른 행은 계속 처리한다.

## 4. 실행

```bash
cd workspace/Naver_Blog_Automation
.venv/bin/python tools/run_snapshot_to_panel.py --demo           # 합성 DEMO
.venv/bin/python tools/run_snapshot_to_panel.py --job 07_DATA/inbox/my_job.json   # 사용자 기록 (MANUAL_IMPORT)
```
Windows에서는 `.venv\Scripts\python.exe tools\run_snapshot_to_panel.py --demo`를 쓴다. 전용 BAT은 P05 범위이고 아직 없다.

## 5. 인수 기준 대응 (P00 §3)

| # | 기준 | 테스트 |
|---|---|---|
| 1 | 기존 회귀 유지 | v1.0 31 + v1.3 19 (BASE 1줄 변경 기록) |
| 2 | A 선택 / B 후순위 / C 제외 | `test_abc_selects_a_ranks_b_excludes_c`, v1.3 `test_offer_level_shipping_and_seller_kept` |
| 3 | 미확인 배송비·옵션·중고·시각·24h·URL 제외 | `test_exclusion_reasons` (10개 subTest) |
| 4 | 가격·URL·시각 동일 Offer | `test_price_url_time_belong_to_same_offer` |
| 5 | 총액 int + 조건 문구, 7열 불변 | `test_selected_maps_total_and_keeps_flags_false`, `test_demo_end_to_end_seven_columns` |
| 6 | DEMO 전 구간 보존 | `test_demo_label_preserved_everywhere` |
| 7 | observed_at 유지, 네이버 None 행 유지, 재실행 무게시 | `test_rerun_keeps_observed_at_and_does_not_publish`, `test_partial_failure_keeps_rows` |
| 8 | 사람 확인 플래그 자동 true 금지 | `test_manual_import_requires_user_recorded_and_stays_hold` |
