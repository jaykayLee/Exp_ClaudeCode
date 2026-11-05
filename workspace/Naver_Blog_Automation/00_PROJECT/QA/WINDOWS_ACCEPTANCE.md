# 사용자 Windows에서 확인할 항목 (P05 갱신 2026-11-05)

제작·검증 환경은 Linux다. 아래 항목은 완료했다고 가정하지 않는다. 각 항목 옆에 날짜와 결과를 적고, `09_LOGS` 폴더를 다음 세션에 올리면 Windows 증거로 쓴다.

## A. 설치 (install.bat)
- [ ] ZIP 전체 해제. 최상단 BAT 파일 **10개**(install, doctor, smoke, start_panel, run_once, run_snapshot, run_snapshot_demo, open_guide, enable/disable_daily_review)와 폴더 존재 확인.
- [ ] **경로에 공백·한글이 있는 폴더**(예: `C:\Users\홍길동\바탕 화면\블로그 작업`)에서도 설치 확인.
- [ ] install.bat에서 Python 탐지 또는 동의한 설치 완료.
- [ ] Pillow==12.3.0 설치와 pip check 성공. 설치 로그 `09_LOGS/install_*.log` 확인.
- [ ] 설치 중 자동 실행되는 테스트가 통과(작업 폴더 + 저장본 애드온 합계, Linux 기준 96개).
- [ ] **재설치**: install.bat을 한 번 더 실행해도 `01_CONFIG/settings.local.json`, `07_DATA/inbox`가 바뀌지 않음.
- [ ] **오프라인 실패 메시지**: 네트워크를 끊고 새 폴더에서 install.bat 실행 → 창이 바로 닫히지 않고 실패 이유와 로그 경로가 보임.

## B. 진단·회귀 (doctor.bat / smoke.bat)
- [ ] doctor.bat: `local_ok=true`, `Pipeline lock: PASS`, `Snapshot add-on: PASS`.
- [ ] smoke.bat: 모든 테스트 통과와 `09_LOGS/test_report.json`의 `suites` 확인.

## C. 작업실 (start_panel.bat)
- [ ] 브라우저에 "로컬 서버 연결 · 자동 발행 OFF" 표시.
- [ ] 데모 3행 생성, 이미지 3개 354×472, 정확한 7열 확인.
- [ ] **다나와 저장본 연결 카드 → "합성 저장본 데모 실행"**: 1행 선택됨(119,000원), 2·3행 보류 사유, 네이버 "미연결".
- [ ] "결과를 위 검토 목록으로 불러오기" → 수정 창의 확인 체크박스가 비어 있음.
- [ ] 한글 상품 입력·가격·이미지 파일 선택·미확인 상태 HOLD 확인.
- [ ] 새 브리프 생성·저장·JSON 내보내기/가져오기 확인.
- [ ] 실행 창 Ctrl+C 종료 후 포트 해제 확인.

## D. 일회 실행 (run_once.bat / run_snapshot*.bat)
- [ ] 빈 인박스에서 run_once.bat → `[INFO] 처리할 입력이 없습니다` (오류 아님), `09_LOGS/daily/run_*.json` 생성.
- [ ] run_snapshot_demo.bat → DEMO_ONLY 결과와 `08_OUTPUT/runs/..._demo_.../bridge/evidence_sidecar.json`.
- [ ] (실제 저장본이 있을 때) `07_DATA/inbox/snapshot_job.json` 작성 후 run_snapshot.bat → HOLD(사람 확인 전 정상).
- [ ] 같은 날 두 번 실행 → 같은 결과 폴더 재사용, 가격 확인시각 유지.
- [ ] 두 창에서 동시에 실행 → 하나는 `PIPELINE_BUSY`로 거절, 잠금 파일은 끝나면 사라짐.

## E. 선택: 일일 로컬 검토 예약 (enable/disable_daily_review.bat)
- [ ] enable: Y/N 확인 후에만 등록, 시간 입력(HH:mm).
- [ ] 작업 스케줄러에서 `BlogWorkspace_LocalReview_xxxxxxxx` 확인 → "지금 실행" → `09_LOGS/daily/`에 새 로그.
- [ ] 마지막 실행 결과 0x0(입력 없음도 0).
- [ ] disable: Y/N 확인 후 해당 작업만 삭제.
- [ ] 예약 작업은 가격 갱신·사이트 수집·로그인·블로그 게시를 하지 않음.

## F. 선택: 이미지 다운로드
- [ ] 허용한 이미지 서버 실제 다운로드 검증(기본은 꺼짐).

실수집·네이버 게시가 구현되지 않은 상태에서 실행 파일이 열린다는 이유만으로 전체 자동화 완료라고 표시하지 않는다.
