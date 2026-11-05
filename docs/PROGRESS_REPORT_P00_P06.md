# 네이버 블로그 자동화 — 진행 정리 (P00 ~ P06)

- 기준일: 2026-11-05 / 기준 문서: `MASTER_IMPLEMENTATION_PROMPT_KO.md`
- 검증 환경: Linux 클라우드 컨테이너, Python 3.13.18, Pillow 12.3.0. **Windows에서는 한 번도 실행하지 않았다.**
- 그림이 들어간 같은 내용: `docs/PROGRESS_REPORT.html` (브라우저로 열기)

---

## 0. 한눈에 보기

| Phase | 목표 | 상태 | 검증 범위 |
|---|---|---|---|
| P00 | 원본·환경 재현, 인터페이스 매핑 | PASS | Linux |
| P01 | 저장본 → 판매자별 검증 → v1.0 → 7열 표 | PASS | Linux·합성 데이터 |
| P02 | 다나와 최소 live pilot | **BLOCKED_EXTERNAL** | 미실행 (허용 경로·실제 저장본 없음) |
| P03 | 네이버쇼핑 가격 경로 | **BLOCKED_EXTERNAL** | 미실행 (허용 경로 없음) |
| P04 | 작업실(HTML 패널) 통합 | PASS | Linux·브라우저 E2E |
| P05 | Windows 설치·일일 로컬 실행 | PASS (Linux) / **NEEDS_WINDOWS_CHECK** | 파이썬 동작 실행 + BAT/PS1 정적 점검 |
| P06 | 배포·수동 네이버 적용 점검 | PASS (Linux) / 네이버 붙여넣기 **NOT_RUN** | 설치형 ZIP 재설치 검증 |
| P07~P10 | — | **정의되지 않음** | 마스터 프롬프트는 P06까지. 제안만 §6에 기재 |

테스트 수(최종): **102개 통과** = 작업 폴더 76 + 저장본 애드온 26. 브라우저 E2E 14/14, 기존 UI QA 15/15.

---

## 1. 전체 흐름 (현재 동작하는 것)

1. 사용자가 다나와 상품 페이지를 브라우저에서 **직접 저장**한다(HTML) → 프로그램은 인터넷에 접속하지 않는다.
2. 같은 폴더에 **확인 기록(meta JSON)**을 쓴다: 대상 모델·옵션, 확인 시각, 판매자 URL별 결제조건(`offer_terms`).
3. **작업 파일(job JSON)**에 상품 목록과 이미지 경로를 적는다 → `07_DATA/inbox/snapshot_job.json`.
4. `run_snapshot.bat` 또는 작업실의 **"작업 파일 실행"** 버튼을 누른다.
5. Snapshot Probe v1.3.1이 HTML 안의 상품·판매자 정보를 읽는다(판매자별 배송비·결제조건 분리).
6. 직접 어댑터가 판매자별로 **다시 검증**한다(모델·옵션·신품·원화·URL·확인시각·배송비·일반결제).
7. 적합한 판매자 중 **배송비 포함 총액이 가장 낮은 판매자**를 고른다(같은 판매자의 가격·URL·시각만 묶음).
8. 기존 v1.0 파이프라인이 이미지를 354×472로 맞추고 **7열 표**를 만든다.
9. 결과 폴더 `08_OUTPUT/runs/<실행ID>/`에 표, 이미지, 근거 파일, 네이버 붙여넣기용 표가 생긴다.
10. 작업실에서 **"결과를 검토 목록으로 불러오기"** → 사람이 모델·옵션과 배송비·조건을 직접 확인하고 체크한다.
11. 체크 후 **"Python 검증 · 표 생성"** → 네이버 가격이 없으므로 결과는 HOLD(정상).
12. 네이버 블로그에는 사람이 직접 로그인해 1행 붙여넣기 시험 후 글을 쓴다. **프로그램은 게시하지 않는다.**

---

## 2. Phase별 상세 (한 줄씩 따라가기)

### P00 — 원본·환경 재현 (앱 코드 변경 없음)
1. 인계 ZIP 무결성 검사 `python tools/verify_handoff.py` → PASS.
2. 작업 폴더 = v1.0 원본 + v1.3 배치본임을 `diff`로 확인 → 차이 없음.
3. venv에 `Pillow==12.3.0`만 설치(lock 그대로).
4. 기존 테스트 v1.0 31개, v1.3 19개 → 모두 통과.
5. 실제 함수 시그니처 추출 → `docs/P00_INTERFACE_MAP.md`.
6. 결함 재현 스크립트 → `00_SESSION/evidence/p00_interface_probe.py`.
   - I02: 공통 배송비 0원이 모든 판매자에 적용 → **카드 전용 80,000원이 최저가로 오선택**.
   - I03: v1.3 출력 열 이름 ≠ v1.0 입력 키 → 그대로 넣으면 가격·URL·시각 소실.
   - I08: v1.0 정규화가 근거 필드(해시 등)를 버림.

### P01 — 저장본 → 7열 표 연결
1. `11_ADDONS/DANAWA_SNAPSHOT_PROBE/probe/snapshot_probe.py` (v1.3.1)
   - 판매자별 `seller`, `shippingDetails`, 조건부 문구(카드·렌탈·쿠폰·할부 등)를 읽는다.
   - 공통 배송비·결제조건은 `offer_terms_scope: "all_offers"`를 명시할 때만 적용한다.
   - 같은 판매자에 대한 기록이 서로 다르면 `SHIPPING_EVIDENCE_CONFLICT`로 보류한다.
2. `03_PROVIDERS/providers/snapshot_adapter.py` (신규, **v1.1/v1.2 재현 아님**)
   - `normalize_snapshot_candidates` → `evaluate_candidates` → `select_lowest_eligible` → `to_panel_input`.
3. `tools/run_snapshot_to_panel.py` (신규 진입점): 기존 `run_pipeline()`을 그대로 호출한다.
4. 근거 보존: `08_OUTPUT/runs/<ID>/bridge/evidence_sidecar.json`.
5. 합성 데모 3상품: `07_DATA/samples/snapshot_demo/`.
6. 결과: A(119,000+0) 선택, B(117,000+5,000=122,000) 2순위, C(카드 전용 80,000) 제외.
7. 사람 확인 체크박스는 프로그램이 **자동으로 켜지 않는다**.

### P02 — 다나와 live pilot → BLOCKED_EXTERNAL
1. 허용된 데이터 경로·이용 조건 확인 자료가 없다.
2. 실제 저장 페이지도 없다 → 실제 다나와 페이지 구조는 **미검증**.
3. P01 연결 코드는 저장본 1개만 있으면 바로 점검할 수 있게 준비되어 있다.

### P03 — 네이버쇼핑 → BLOCKED_EXTERNAL
1. 기존 쇼핑 검색 API는 종료됐다(인계 문서 기준이며 이번 세션에서 재확인하지 않음).
2. 허용된 대체 경로가 없어 네이버 열은 **"미수집"** 으로 둔다(0원으로 표시하지 않음).

### P04 — 작업실(HTML 패널) 통합
1. 서버: `tools/server.py`에 `POST /api/snapshot` 추가(토큰·Host·Origin 검사 그대로, `07_DATA` 밖 경로 거부).
2. 화면: `06_UI/index.html` 작업실에 **"다나와 저장본 연결 · 수집 상태"** 카드 추가.
   - 버튼: 합성 저장본 데모 실행 / 작업 파일 실행 / 결과를 검토 목록으로 불러오기.
   - 상품별 상태: 선택됨(총액=상품가+배송비·판매자) / 보류(한국어 사유) / 네이버 미연결.
3. 사람 확인 흐름(I13 해결): 불러온 목록의 수정 창에서 체크 → 기존 "Python 검증 · 표 생성".
4. 이미지 검증: 3장 모두 354×472·300dpi, 원본 파일 해시 불변, 투명 배경은 흰색, 손상·누락 이미지여도 가격 행 유지.
5. 모바일 화면에서 상태 표가 잘리던 문제 → 카드 안 가로 스크롤로 수정.
6. 브라우저 E2E 14/14(실제 로컬 서버, 공백·한글 경로, 데스크톱+모바일).

### P05 — 설치·일일 로컬 실행
1. `tools/run_once.py` (일일 실행)
   - `07_DATA/inbox/products.json`(직접 입력)과 `07_DATA/inbox/snapshot_job.json`(저장본 작업)을 **각각** 처리.
   - 한쪽이 실패해도 다른 쪽 결과를 남긴다(exit 1 + 로그).
   - 입력이 없으면 오류가 아니라 **NO_INPUT(exit 0)** + 한국어 안내(I10 해결).
   - 매 실행 기록: `09_LOGS/daily/run_<시각>.json`.
   - 동시 실행은 `PIPELINE_BUSY`로 거절, 잠금 파일은 자동 삭제하지 않고 경과 시간을 보여준다.
2. 새 BAT: `run_snapshot.bat`, `run_snapshot_demo.bat` (기존 BAT과 같은 형식: ASCII, CRLF, UTF-8 콘솔).
3. `smoke.bat`(= `qa_runner.py`)이 저장본 애드온 테스트까지 함께 실행.
4. `doctor.bat`에 잠금 파일·애드온 점검 항목 추가.
5. 정적 점검 테스트: 모든 BAT의 줄바꿈·인코딩·경로 따옴표, 예약 등록 전 Y/N 확인, 무인 실행 스크립트에 입력 대기 없음.
6. Windows 확인 체크리스트 갱신: `00_PROJECT/QA/WINDOWS_ACCEPTANCE.md` (A 설치 ~ F 이미지 다운로드).

### P06 — 배포·수동 네이버 적용 점검
1. `tools/build_release.py`: 설치형 ZIP 생성.
   - 제외: 설정(`settings.local.json`), 인박스 입력, 원본·변환 이미지, 실행 결과, 로그, 브리프, venv, 캐시.
   - `products.json`은 빈 기본값으로 새로 넣는다.
   - 비밀번호·키·토큰 형태 값이 보이면 빌드를 멈춘다.
2. 깨끗한 설치 검증(공백·한글 경로): venv → lock 설치 → pip check → doctor → 102 테스트 → 재설치 시 설정 보존 → 데모.
3. 이 검증에서 빌더 버그 1건 발견·수정: 설치본에서 다시 빌드하면 이전 매니페스트가 섞이던 문제.
4. 네이버 붙여넣기용 표 `naver_paste_table.html`: 인라인 스타일만, 이미지 칸은 업로드 파일명, 상단에 DEMO/HOLD 경고.
5. 작업실 가이드 갱신: 1행 붙여넣기 시험 안내, 일일 실행 설명, 이번 배포 확인 범위, Gate 2·3 BLOCKED 표시.

---

## 3. 사용자가 실행할 순서 (Windows)

1. `Naver_Blog_Automation_P06_20261105.zip`을 **전체 해제**한다(경로에 한글·공백 있어도 됨 — Linux에서만 확인).
2. `install.bat` → 설치 로그 `09_LOGS/install_*.log`.
3. `doctor.bat` → `local_ok: true`.
4. `smoke.bat` → 102개 통과 여부.
5. `start_panel.bat` → 브라우저 작업실 → "합성 저장본 데모 실행".
6. `run_once.bat` → 빈 인박스면 "처리할 입력이 없습니다"(정상).
7. 결과 폴더의 `naver_paste_table.html`을 열어 **1행만** 네이버 에디터에 붙여넣기 시험.
8. 체크리스트 `00_PROJECT/QA/WINDOWS_ACCEPTANCE.md`에 결과 표시 → `09_LOGS` 폴더와 함께 다음 세션에 전달.

---

## 4. 미검증 · 막힘 (정직한 목록)

1. Windows: BAT·PowerShell·작업 스케줄러 **전부 미실행**.
2. 실제 다나와 페이지: 구조·판매자 배송비 표기 형태 **미검증**.
3. 네이버쇼핑 가격: 경로 없음.
4. 네이버 에디터 붙여넣기 유지 여부: **미검증**.
5. 네이버 게시: 구현하지 않음(`auto_publish=false` 유지).
6. v1.1/v1.2 원본: 없음. 직접 어댑터 사용.
7. 실제 사용자 기록 작업 파일(job/meta)은 직접 JSON으로 작성해야 한다(작성 화면 없음).

---

## 5. 파일 지도 (바뀐 곳만)

| 구분 | 파일 | Phase |
|---|---|---|
| 수정 | `11_ADDONS/DANAWA_SNAPSHOT_PROBE/probe/snapshot_probe.py` (+테스트, manifest, 템플릿, SHA256SUMS) | P01 |
| 신규 | `03_PROVIDERS/providers/snapshot_adapter.py` | P01 |
| 신규 | `tools/run_snapshot_to_panel.py` | P01·P04 |
| 신규 | `07_DATA/samples/snapshot_demo/*` | P01 |
| 수정 | `tools/server.py` (`/api/snapshot`, 붙여넣기 표 링크) | P04·P06 |
| 수정 | `06_UI/index.html` (저장본 카드, 가이드 문구) | P04·P06 |
| 재작성 | `tools/run_once.py` | P05 |
| 수정 | `tools/qa_runner.py`, `tools/doctor.py` | P05 |
| 신규 | `run_snapshot.bat`, `run_snapshot_demo.bat` | P05 |
| 신규 | `tools/build_release.py`, `02_CORE/exporters/naver_paste.py` | P06 |
| 신규 | `10_TESTS/test_snapshot_bridge.py`, `test_panel_integration.py`, `test_daily_ops.py`, `test_release_and_paste.py` | P01~P06 |
| 수정 | `00_PROJECT/QA/WINDOWS_ACCEPTANCE.md`, `00_PROJECT/QA/developer_ui_qa.py`(선택자), `00_PROJECT/CHANGELOG.md` | P05·P06 |
| **변경 없음** | `02_CORE/nbcore/*`, `02_CORE/exporters/table_exporter.py`, `providers/base.py`, `install.bat`, `tools/bootstrap.ps1`, `tools/schedule.ps1` | — |

---

## 6. P07 ~ P10 제안 (실행하지 않음 — 범위 결정 필요)

마스터 프롬프트의 Phase는 P06에서 끝난다. 아래는 현재 상태에서 자연스러운 다음 단계 후보이며, 순서·범위는 사용자가 정한다.

1. **P07 · Windows 실기 반영**
   - 입력: 체크리스트 결과 + `09_LOGS`.
   - 할 일: 설치·BAT·예약 문제 수정, `NEEDS_WINDOWS_CHECK` 항목을 실제 결과로 교체.
2. **P08 · 실제 다나와 저장본 1개 점검** (= P02 A안)
   - 입력: 직접 저장한 상품 페이지 HTML 1개 + 확인 시각 + 정확한 모델·옵션.
   - 할 일: 실제 JSON-LD·판매자 정보 형태 확인, 필요 시 probe 보완. 네트워크 요청 없음.
3. **P09 · 저장본 작업 파일 작성 화면**
   - 입력: 없음(결정만).
   - 할 일: 작업실에서 HTML 선택·확인시각·판매자별 결제조건을 입력해 job/meta JSON을 만드는 폼(I12).
4. **P10 · 게시 계층 준비 (선택)**
   - 입력: 사용할 플랫폼과 인증 방식 결정(네이버는 공개 게시 API 전제를 두지 않음).
   - 할 일: 초안 저장 수준의 Publisher 구현 검토. 자동 공개 발행은 별도 승인 전까지 하지 않음.
