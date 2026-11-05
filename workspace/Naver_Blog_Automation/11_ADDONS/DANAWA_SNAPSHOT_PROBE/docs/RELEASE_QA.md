# v1.3 QA Results — 2026-11-01

- 구현: 오프라인 HTML 파일의 JSON-LD Product/Offer 파서, AggregateOffer 제외, 모델/옵션/결제/배송비/확인시각/승인여부 HOLD, 입력 SHA-256, 리뷰용 CSV, JSON/HTML 보고서, BAT 실행 진입점.
- Python 단위 시험: **19 PASS** (`python -m unittest discover -s tests -v`). 합성 HTML을 사용했고 외부 네트워크 접근은 실행하지 않음.
- CLI 데모: `python -m probe.snapshot_probe demo --out output/demo` → `DEMO_ONLY`, 후보 2건 발견, CSV 데이터 행 0건 (예제의 실제 발행 방지).
- 합성 수동 모드: `fixtures/demo_product.html` + `fixtures/manual_meta_template.json` → `HOLD_REVIEW`, 권한/실제 시간 등 미확인 표시.
- HTML 안내: Chromium `set_content()` 데스크톱 1280px/모바일 390px 기본 렌더링 및 가로 overflow 없음 확인. 실제 Windows 브라우저의 `file:///` 실행은 별도 확인 필요.
- BAT: UTF-8/CRLF 구조·상대경로 정적 확인만 완료. **Windows BAT 실제 실행 미검증**.
- 기존 v1.0/v1.1/v1.2 ZIP: 해당 대화 첨부 참조로 접근을 시도했으나 원본 ZIP 파일을 실행 환경에 복사할 수 없어 실제 통합 회귀 테스트 **미실시**.
- 실제 다나와 페이지 저장본: 미제공, 구조 파싱 결과 **미검증**.
- 네이버쇼핑 API: 2026-07-31 종료(공식 공지). 대체 공개 가격 API 연결 기능 없음.
- 최종 블로그 자동 게시: 구현 범위 아님. 이미지 다운로드/리사이즈도 이번 Add-on에서 구현/수정하지 않음.

## Windows 사용자 수용 시험
1. `doctor.bat`: Python ≥3.11<3.14 및 기존 프로젝트 경로 확인.
2. `smoke.bat`: 19 PASS.
3. `run_demo.bat`: output/demo/snapshot_report.html에 DEMO_ONLY 및 후보 2건, CSV 데이터 행 0건.
4. `run_snapshot.bat` (실제 허용된 HTML + 검토 메타): `snapshot_report.json`과 `snapshot_report.html`에 구조 및 HOLD 사유.
5. v1.2 CSV Bridge에 직접 연결하기 전에 정확한 헤더·열 타입·검증 상태를 대조하고 저장본 백업을 유지.
