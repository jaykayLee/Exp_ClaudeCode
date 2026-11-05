# 미해결 사항 (P06 갱신 2026-11-05)

| ID | 우선순위 | 상태 | 문제와 다음 조치 |
|---|---|---|---|
| I01 | P0 | BLOCKED_INPUT | v1.1/v1.2 원본 미확보. 신규 직접 어댑터로 대체했다(`LEGACY_V11_V12_COMPATIBILITY_UNVERIFIED`). |
| I02 | P0 | RESOLVED (P01, 합성) | 판매자별 배송비·결제조건. 실제 다나와 HTML 형태는 미검증. |
| I03 | P0 | RESOLVED (P01) | v1.3 → v1.0 입력 변환. |
| I04 | P0 | BLOCKED_EXTERNAL | 다나와 허용 경로·실제 저장본 없음. 사용자가 저장한 상품 페이지 HTML 1개가 있으면 오프라인 구조 점검이 가능하다. |
| I05 | P1 | BLOCKED_EXTERNAL | 네이버쇼핑 가격 경로 없음. 네이버 열은 "미수집" 유지. |
| I06 | P1 | PARTIAL (P07) | CI Windows Server에서 install/doctor/smoke/run_once/run_snapshot_demo/재설치/서버/브라우저 E2E 통과. 사용자 PC와 작업 스케줄러는 미실행. `00_PROJECT/QA/WINDOWS_ACCEPTANCE.md` A~F 순서로 확인하고 `09_LOGS`를 회신한다. |
| I07~I09 | — | RESOLVED (P01) | DEMO 하네스, 근거 sidecar, 신선도 기준 통일. |
| I10 | P2 | RESOLVED (P05) | 빈 인박스 → NO_INPUT(exit 0) + 안내 + 실행 로그. |
| I11 | P2 | PARTIAL | 스냅샷 후보 URL은 https만 허용한다. v1.0 수동 입력은 http도 허용한다. 통일하려면 사용자 결정이 필요하다(기존 입력 호환성 영향). |
| I12 | P2 | OPEN | 실제 사용자 기록(MANUAL_IMPORT) 저장본 작업은 job·meta JSON을 손으로 작성해야 한다. 작성 화면은 없다(템플릿·예시만 있음). |
| I13 | P1 | RESOLVED (P04) | 브리지 결과 → 검토 목록 → 사람 체크 → MANUAL_IMPORT 흐름. |
| I14 | P3 | NOTE | P00 probe의 `I02_offer_level_seller_shipping_dropped`는 키 이름을 글자 그대로 검사해 계속 CONFIRMED로 출력된다(실제로는 해결됨). |
| I15 | P1 | NOT_RUN | `naver_paste_table.html`을 네이버 에디터에 붙여넣었을 때 표·링크가 유지되는지 미검증이다. 1행 시험 결과를 회신해야 한다. |
| I16 | P3 | NOTE | UI 브라우저 QA는 개발용 Playwright(Python)가 필요하다. 배포 의존성(lock)에는 넣지 않았다. |
| I17 | P2 | DECISION_NEEDED | P07~P10은 마스터 프롬프트에 정의되지 않았다. 제안 목록: `docs/PROGRESS_REPORT_P00_P06.md` §6. |
| I18 | P3 | RESOLVED (P07) | 문서 수정 후 매니페스트를 갱신하지 않으면 CI 무결성 검사가 실패한다 → `tools/write_manifest.py`를 마지막에 실행(release-package 스킬에 반영). |
