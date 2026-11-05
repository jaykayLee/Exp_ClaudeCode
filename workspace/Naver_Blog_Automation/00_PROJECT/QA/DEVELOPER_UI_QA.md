# UI 검사 재현용 개발 도구

developer_ui_qa.py는 배포 검증에 사용한 Playwright 검사입니다. 일반 사용자 설치에 Playwright/Chromium을 추가하지 않습니다. Linux 개발 검사에만 사용하며 Chromium 경로는 /usr/bin/chromium입니다. 이 도구를 실행하는 것은 필수 설치 절차가 아닙니다.

통상 사용자 검사는 smoke.bat와 HTML 작업실에서 수행합니다. 실제 Windows 브라우저 접속 여부는 별도로 확인해야 합니다.
