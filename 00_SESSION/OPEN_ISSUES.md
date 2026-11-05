# 미해결 사항 (P01 갱신 2026-11-05)

| ID | 우선순위 | 상태 | 문제와 다음 조치 |
|---|---|---|---|
| I01 | P0 | BLOCKED_INPUT | v1.1/v1.2 원본 미확보. P01은 신규 직접 어댑터로 대체했다(`LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED`). 원본이 제공되면 해시·인터페이스·테스트를 대조한다. |
| I02 | P0 | RESOLVED (P01, 합성 검증) | v1.3.1에서 판매자별 배송비·결제조건을 분리했다. A/B/C 회귀 PASS. 실제 다나와 HTML에서 seller/shippingDetails가 어떤 형태인지는 미검증이다(P02). |
| I03 | P0 | RESOLVED (P01) | `to_panel_input`으로 v1.0 키에 연결했다. 가격·URL·시각을 같은 Offer에서 가져온다. |
| I04 | P0 | BLOCKED_EXTERNAL | 다나와의 허용된 데이터 경로·이용 범위가 미확정이다. P02 시작 전 사용자 확인이 필요하다. |
| I05 | P1 | BLOCKED_EXTERNAL | 네이버쇼핑 대체 경로가 미확정이다. 종료 공지는 재확인하지 않았으며 P03 시작 시 재확인한다. |
| I06 | P1 | NEEDS_WINDOWS_CHECK | BAT 설치·실행·예약은 실제 Windows 로그가 필요하다. P01 브리지용 BAT은 아직 없다(P05). |
| I07 | P1 | RESOLVED (P01) | DEMO 하네스(`snapshot_demo/job.json` + `test_snapshot_bridge.py`)로 DEMO_ONLY를 끝까지 보존한다. |
| I08 | P0 | RESOLVED (P01) | `<run>/bridge/evidence_sidecar.json`에 근거 필드를 보존한다. |
| I09 | P2 | RESOLVED (P01) | v1.0 `max_price_age_hours`를 v1.3.1 `fresh_hours`와 어댑터에 같은 값으로 전달한다. |
| I10 | P2 | OPEN | 인박스 기본 `records: []` 상태에서 비데모 run_once는 exit 1이다. P04/P05에서 한국어 안내와 함께 처리한다. |
| I11 | P2 | PARTIAL | 스냅샷 후보 URL은 https만 허용한다. v1.0의 http 허용은 그대로다. P04에서 통일 여부를 결정한다. |
| I12 | P2 | OPEN | 사용자가 MANUAL_IMPORT 브리지를 쓰려면 job·meta JSON을 손으로 작성해야 한다(템플릿만 있음). 작성 UI·검증 안내는 P04 범위다. |
| I13 | P2 | OPEN | 브리지 결과는 사람 확인 플래그를 자동으로 true로 만들지 않아 MANUAL_IMPORT에서 항상 HOLD다. 패널에서 사람이 확인 표시하는 흐름은 P04 범위다. |
| I14 | P3 | NOTE | `00_SESSION/evidence/p00_interface_probe.py`의 `I02_offer_level_seller_shipping_dropped`는 키 이름을 글자 그대로 검사한다. P01 이후에도 CONFIRMED로 출력되지만 실제로는 해결됐다(TEST_RESULTS.json 참고). P00 증거 보존을 위해 수정하지 않았다. |
