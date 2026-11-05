# 미해결 사항 (P00 갱신 2026-11-05)

| ID | 우선순위 | 상태 | 문제와 다음 조치 |
|---|---|---|---|
| I01 | P0 | BLOCKED_INPUT | v1.1/v1.2 원본 미확보(P00 재확인). 원본이 제공되면 해시·인터페이스·테스트를 검사한다. 제공되지 않으면 P01에서 신규 직접 어댑터를 쓰고 `LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED`로 남긴다. |
| I02 | P0 | OPEN (재현됨) | v1.3 `inspect_snapshot`이 meta 배송비·결제조건을 모든 Offer에 적용한다. A/B/C 합성에서 카드 전용 C(80000)가 단순 최저가로 오선택된다. `offer_candidates`는 seller·shippingDetails를 버린다. 재현: `00_SESSION/evidence/p00_interface_probe.py`. P01 §3 수정. |
| I03 | P0 | OPEN (재현됨) | v1.3 CSV 열과 v1.0 입력 키가 불일치한다. 그대로 넣으면 가격·URL·시각이 소실된다. P01 `to_panel_input`. |
| I04 | P0 | BLOCKED_EXTERNAL | 다나와 운영 데이터 경로·이용 범위가 확정되지 않았다. P02 live pilot 전에 확인한다. |
| I05 | P1 | BLOCKED_EXTERNAL | 네이버쇼핑 종료 API를 대체할 허용 경로가 확정되지 않았다. 종료 공지는 이번 세션에서 재확인하지 않았으며 P03 시작 시 재확인한다. |
| I06 | P1 | NEEDS_WINDOWS_CHECK | BAT 설치·일일 예약은 실제 Windows 로그가 필요하다. 예약 작업은 python으로 run_once.py를 직접 호출하므로 run_once.bat의 pause와 무관하다(코드 확인). |
| I07 | P1 | OPEN | DEMO_ONLY를 끝까지 보존하는 E2E 하네스가 필요하다. v1.3 `run(demo=True)`는 observed_at을 현재 시각으로 바꾸므로 하네스는 `inspect_snapshot(now=...)`를 직접 호출한다. |
| I08 | P0 | OPEN | v1.0 `normalize_records`가 source_kind·snapshot_sha256·evidence_kind·candidate_id·shipping_fee를 버린다. P01 evidence_sidecar.json. |
| I09 | P2 | OPEN | 신선도 기준이 이원화돼 있다(v1.3 하드코딩 24h, v1.0 설정 1~168h). P01에서 v1.0 설정값을 v1.3에 인자로 전달한다. |
| I10 | P2 | OPEN | 인박스 기본 `records: []` 상태에서 비데모 run_once는 exit 1이다. P04/P05에서 한국어 안내 메시지와 함께 처리한다. |
| I11 | P2 | OPEN | v1.0 `public_link`는 http를 허용하고 v1.3 `safe_https_url`은 https만 허용한다. 링크 정책을 P01/P04에서 통일한다(기본은 https 권장, 결정 필요). |
