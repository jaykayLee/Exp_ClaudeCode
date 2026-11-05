# Naver Blog Cloud Handoff v1.0

START_HERE.html을 브라우저에서 연다. 마스터 프롬프트와 이 ZIP을 코딩 세션에 올리고 P00부터 시작한다.

- 수정할 코드: workspace/Naver_Blog_Automation
- 변경 금지 원본: reference/originals
- 세션 상태: 00_SESSION
- 최초 무결성 확인: python tools/verify_handoff.py 또는 verify_handoff.bat
- 기본 규칙: 1세션 1Phase, 실제 시험만 PASS, 종료 시 ZIP+MD 체크포인트
- 누락: v1.1/v1.2 원본. 세부 내용은 SOURCE_INVENTORY.json.
- 이 파일은 구현을 위한 인계 패키지이며 자동 수집·게시 완성본이 아니다.

Windows에서 실제 앱 설치를 시험할 때는 workspace/Naver_Blog_Automation/install.bat를 사용한다. 설치는 네트워크와 사용자 정책에 영향을 받는다. 최초 무결성 확인 후 수행하고, .venv나 실제 사용자 설정은 다음 인계 ZIP에서 제외한다.

## Git · CI (2026-11-05 추가)
- 이 폴더가 git 저장소 루트다. 로컬 커밋으로 Phase별 체크포인트가 남아 있다.
- `.github/workflows/ci.yml`: push 시 Linux 테스트와 **실제 Windows 러너에서 BAT 실행**(공백·한글 경로). 결과물로 설치 ZIP과 로그를 내려받을 수 있다.
- 새 세션 시작: `bash scripts/cloud_session_setup.sh` → `00_SESSION/PHASE_HANDOFF.md`.
- 다음 작업 후보: `docs/BACKLOG_P07_P10.md`.
