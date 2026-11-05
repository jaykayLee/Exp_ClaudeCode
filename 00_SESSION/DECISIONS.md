# 결정 기록

2026-11-05 — 특정 코딩 서비스·모델·크레딧 숫자는 전제하지 않는다.
2026-11-05 — 앱 기능과 별개인 인계 패키지 v1.0으로 명명한다. 앱 v1.4 완성본이라고 부르지 않는다.
2026-11-05 — v1.0/v1.3 원본 보존. 작업용 사본은 배치만 하고 원래 코드를 변경하지 않았다.
2026-11-05 — 누락 v1.1/v1.2 호환성은 추측하지 않는다. 직접 어댑터 대안은 신규 코드로 명확히 구분한다.
2026-11-05 — 1세션=1Phase, Phase 종료 후 STOP, 최신 ZIP+MD로 재개한다.
2026-11-05 — 자동 발행·유료 API·공개 배포·예약 등록은 기본 비활성화다.
2026-11-05 (P00) — P01은 v1.0 Core(validation/pipeline/table_exporter/PriceCandidate)를 수정하지 않고 신규 `providers/snapshot_adapter.py` + `tools/run_snapshot_to_panel.py`로 연결한다. 근거: v1.0 외부 인터페이스 보존, 31개 회귀 유지.
2026-11-05 (P00) — I02 수정 방식: v1.3에서 offer 단위 배송비·결제조건을 우선한다. meta 공통값은 `offer_terms_scope: "all_offers"` 명시 시에만 전 후보에 적용한다. 기존 테스트 `BASE` meta에 이 키 1줄 추가가 필요하며 이는 의도적 계약 변경이다.
2026-11-05 (P00) — v1.0에 넣는 `danawa_price`는 배송비 포함 일반 구매 총액(int)이다. 상품가·배송비 분해와 근거는 `danawa_condition` 문구와 evidence sidecar에 둔다. 7열은 바꾸지 않는다.
2026-11-05 (P00) — `*_match_checked`/`*_terms_checked`는 사람 확인 플래그로 유지한다. 어댑터가 자동으로 true로 만들지 않는다.
2026-11-05 (P00) — 체크포인트는 로컬 git으로 관리한다(원격 push 없음). 인계 ZIP에는 .git/.venv/캐시/settings.local.json을 넣지 않는다.
2026-11-05 (P01) — 판매자별 결제조건의 근거는 meta `offer_terms`(URL별 사용자 기록)로 받는다. schema.org에는 "일반 결제" 표준 필드가 없으므로 HTML만으로 normal을 추정하지 않는다.
2026-11-05 (P01) — Offer 문구에 카드·렌탈·약정·쿠폰·할부·월 납입 등이 있으면 사용자가 normal로 기록해도 보류한다(보수적 선택).
2026-11-05 (P01) — 총액 동률은 상품가가 낮은 쪽 → candidate_id 순서로 결정하고 `ties`에 남긴다.
2026-11-05 (P01) — `run_snapshot_to_panel(input_paths, root)`: 출력 폴더 인자 대신 v1.0의 `08_OUTPUT/runs/<id>/bridge/`를 사용한다(기존 출력 구조 유지).
2026-11-05 (P01) — DEMO에서는 v1.3을 demo=True로 호출해 CSV 0건 계약을 지키고, DEMO_ONLY는 선택 연습에서 라벨로만 취급한다. 합성 고정 평가시각(`evaluation_time`)은 DEMO job에서만 허용한다.
2026-11-05 (P01) — 스냅샷 경로의 evidence_kind는 synthetic(DEMO)·user_recorded(MANUAL_IMPORT)만 허용하고 live_verified는 거부한다.
2026-11-05 (P01) — 링크 정책(I11): 스냅샷 후보 URL은 https만 허용한다. v1.0의 http 허용 정책은 바꾸지 않았다(P04에서 통일 여부 결정).
