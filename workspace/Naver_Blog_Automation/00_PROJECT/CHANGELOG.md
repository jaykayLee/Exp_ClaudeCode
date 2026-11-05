# 변경 기록

## v1.0.0 — 2026-10-11
- 반복 주차 안내를 실제 구현·검증 여부 기준의 프로젝트로 재정리.
- 기존 v0.4는 오프라인 7열 HTML exporter만 포함함을 확인. 원본 ZIP 보존.
- Windows 설치/BAT·로컬 서버·한국어 HTML 가이드·상품 입력 팝업·JSON 저장/가져오기 구현.
- 이미지 권한 선언·원본 해시/증거 저장·EXIF 보정·흰 여백/비율 유지·규격 출력 구현.
- HTTPS 이미지 다운로드를 권한·허용 호스트·공인 IP·크기 제한으로 기본 비활성화. 다운로드는 모의 응답 검증만 수행.
- 가격 문자열의 여러 숫자를 합쳐 버리는 방식 제거. 한 가격만 파싱.
- 모델/조건/확인시각/누락/권한을 검사하고 부분 실패에도 행 유지. 재생성해도 가격 확인시각 불변.
- 중복 동시 실행 잠금과 이전 생성 이미지의 잔존 제거.
- 네이버 쇼핑 검색 API의 2026-07-31 종료 공지 반영. 과거 API 호출 코드는 구현하지 않음.
- 새 글 설계용 브리프 생성·근거 레지스트리 추가. 타인의 글 전문·이미지 복제 없음.
- Blogger/WordPress는 발행 인터페이스와 확장 가이드만 제공.
- 일일 작업은 사용자 실행·확인 후 등록하는 로컬 자료 검토 작업이며 가격 갱신/발행 아님.

보존한 v0.4 SHA256: `2a50b3da09b497cd26ef28788c4fcf03abc50025d71c5cb97e4d1bdb8ab1695f`

## P01 (인계 패키지 작업) — 2026-11-05
- v1.0 Core는 변경하지 않음. 신규 `providers/snapshot_adapter.py`(직접 어댑터, v1.1/v1.2 재현 아님)와 `tools/run_snapshot_to_panel.py` 추가.
- Snapshot Probe v1.3.1: 판매자별 배송비·결제조건 근거 분리. 공통 meta는 `offer_terms_scope: "all_offers"` 명시 시에만 적용.
- 합성 DEMO job(`07_DATA/samples/snapshot_demo`)과 인수 테스트 19개(`10_TESTS/test_snapshot_bridge.py`) 추가.
- Linux에서만 검증함. Windows BAT·실제 다나와/네이버 수집·게시는 미검증.

## P04~P06 (인계 패키지 작업) — 2026-11-05
- P02·P03: 외부 조건으로 BLOCKED_EXTERNAL (다나와 허용 경로·실제 저장본 없음, 네이버쇼핑 가격 경로 없음).
- P04: 작업실에 "다나와 저장본 연결 · 수집 상태" 카드, `POST /api/snapshot`, 결과 → 검토 목록 → 사람 체크 흐름. 모바일 표 스크롤 수정.
- P05: `run_once.py`가 products.json과 snapshot_job.json을 각각 처리, 입력 없음은 exit 0, 실행 로그 `09_LOGS/daily/`. `run_snapshot.bat`, `run_snapshot_demo.bat` 추가. smoke에 애드온 테스트 포함. doctor에 잠금 파일 점검.
- P06: 설치형 ZIP 빌더 `tools/build_release.py`(사용자 데이터·비밀정보 제외), 네이버 붙여넣기 시험용 표 `naver_paste_table.html`, 가이드 갱신.
- v1.0 핵심(nbcore, table_exporter, providers/base, install/bootstrap/schedule)은 변경하지 않음.
- Linux에서만 검증. Windows 실행·네이버 에디터 붙여넣기·실시간 수집은 미검증.
