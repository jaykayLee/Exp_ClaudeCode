# 네이버 블로그 작업실 v1.0.0

## 가장 먼저
1. ZIP을 짧은 로컬 경로에 완전히 해제합니다. 예: C:\BlogWorkspace\Naver_Blog_Automation
2. install.bat 더블클릭 → Python이 없으면 설치 동의 Y → 완료 메시지 확인.
3. start_panel.bat 더블클릭 → 로컬 브라우저 작업실 → 데모 3개 → Python 검증·표 생성.

설명만 보려면 open_guide.bat 또는 06_UI/index.html을 엽니다. HTML 단독은 Python 저장/변환과 연결되지 않습니다.
전체 절차·네이버 적용·문제 해결·확장·참고 출처는 06_UI/index.html에 있습니다.

## 무엇이 실제로 되는가
- 상품 팝업 입력, 직접 확인한 가격 입력, JSON 가져오기/내려받기.
- 사용 가능한 이미지의 원본 보존, 354x472px/300dpi 선택 프리셋, 비율 유지 리사이즈.
- 정확한 7열 HTML 표, 누락 처리, 가격 확인시각/모델/조건/권한 검토 보고서.
- 내 근거 기반 콘텐츠 브리프 생성, MD 저장, 수동 네이버 게시 준비.
- 선택: 권한·호스트를 지정한 HTTPS 이미지 다운로드. 외부 호스트 실동작은 별도 확인 필요.

## 무엇이 아직 안 되는가
- 실제 다나와/네이버쇼핑 자동 가격 수집.
- 네이버 블로그 로그인, 서버 임시저장, 이미지 업로드, 공개 발행.
- Blogger/WordPress 실제 API 호출.

네이버 공식 공지상 Shopping Search API는 2026-07-31 종료됐으며 대체 API도 제공되지 않습니다.
https://developers.naver.com/notice/article/32530

## 운영
일상 실행은 start_panel.bat 하나입니다. CMD 창은 사용 중 열어 둡니다. 종료는 Ctrl+C.
진단 doctor.bat / 테스트 smoke.bat / 운영 입력 1회 처리 run_once.bat.
선택 예약 enable_daily_review.bat / 해제 disable_daily_review.bat.
예약은 저장된 입력 재검토·이미지·표만 처리합니다. 최신 가격으로 갱신하거나 게시하지 않습니다.

## 검증
31개 Python·로컬 HTTP 테스트와 15개 브라우저 UI 검사, 이전 원본 테스트 2개를 확인했습니다.
Windows 실제 설치·BAT·예약은 사용자 PC 검증이 필요합니다. 상세 방식은 00_PROJECT/QA/TEST_SCOPE.md.
이 프로젝트는 비공개 로컬 작업실이며 공개 호스팅 서비스가 아닙니다.
