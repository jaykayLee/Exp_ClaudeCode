# 이어하기 상태 — P01 완료 (2026-11-05)

P01만 수행했다. P02는 시작하지 않았다(외부 입력 필요).

## 구현한 것
- **Snapshot Probe v1.3.1**: 판매자별 배송비·결제조건·판매자 근거를 분리했다. 공통 meta 값은 `offer_terms_scope: "all_offers"` 명시 시에만 적용한다. 조건부 가격 문구는 보류하고, `fresh_hours`로 신선도 기준을 전달한다.
- **`providers/snapshot_adapter.py`** (신규 직접 어댑터, v1.1/v1.2 아님): 후보 계약 정규화 → 독립 재검증 → 총액 최저가 선택 → v1.0 입력 변환.
- **`tools/run_snapshot_to_panel.py`**: 단일 진입점(`--demo`, `--job`). 기존 v1.0 `run_pipeline`을 그대로 호출한다. `bridge/evidence_sidecar.json`에 근거를 보존한다.
- **합성 DEMO job** 3상품과 **인수 테스트 19개**.
- v1.0 Core(nbcore/exporters/base/UI/BAT)는 **변경 없음**.

## 실행한 검사 (Linux, Python 3.13.18, Pillow 12.3.0)
- v1.0 `tools/qa_runner.py`: **50/50 OK** (기존 31 + 브리지 19)
- v1.3.1 unittest: **26/26 OK** (기존 19 + 신규 7. 기존 1개는 BASE에 scope 1줄을 추가한 의도적 계약 변경)
- `run_snapshot_to_panel.py --demo`: DEMO_ONLY, 1행 A 119,000원, 2·3행 HOLD(사유 표시). 스크린샷은 `evidence/P01/demo_table_screenshot.png`
- 애드온 CLI demo: DEMO_ONLY, CSV 0건(계약 유지)
- 작업 중 발견·수정한 버그: 어댑터 재검증의 문자열 가격 TypeError(테스트가 잡아냄)

## 미검증
Windows BAT, 실제 다나와 HTML 구조, 네이버쇼핑, 네이버 게시, 네이버 API 종료 공지 재확인.

## 재현
```bash
cd workspace/Naver_Blog_Automation && python3 -m venv .venv && .venv/bin/pip install -r tools/dependencies.lock
.venv/bin/python tools/qa_runner.py
(cd 11_ADDONS/DANAWA_SNAPSHOT_PROBE && ../../.venv/bin/python -m unittest discover -s tests -v)
.venv/bin/python tools/run_snapshot_to_panel.py --demo
cd ../.. && python3 tools/verify_release.py
```

## 다음 단일 Phase
- **P02 (다나와 최소 live pilot)**: 사용자가 다음 두 가지를 먼저 줘야 한다. ① 허용된 다나와 데이터 경로(제공 API·피드·저장 허용 페이지)와 이용 조건 확인 근거, ② 확인 가능한 실제 상품 1개(정확한 모델·옵션). 없으면 P02는 `BLOCKED_EXTERNAL`이다.
- 대안: 사용자가 브라우저로 직접 저장한 다나와 HTML 1개 + meta(`user_recorded`)로 **실제 페이지 구조만 오프라인 점검**하는 것은 P02의 일부로 가능하다(네트워크 요청 없음).
- P02/P03이 막히면 요청 시 P04(이미지·7열·HTML 패널 통합)를 수동 입력으로 진행할 수 있다.
