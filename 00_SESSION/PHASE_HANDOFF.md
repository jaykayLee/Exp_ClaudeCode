# 이어하기 상태 — P00 완료 (2026-11-05)

P00만 수행했다. 앱 코드(`workspace/Naver_Blog_Automation`의 .py/.bat/.json)는 **한 줄도 바꾸지 않았다.** P01은 시작하지 않았다.

## 이번 Phase에서 한 것
1. 인계 ZIP(sha256 `1792df83…0fcd`) 해제 → `python3 tools/verify_handoff.py` **PASS**(수정 전 원본 상태).
2. workspace = v1.0 원본 ZIP 해제본 + v1.3 원본을 `11_ADDONS/DANAWA_SNAPSHOT_PROBE`에 배치만 한 상태임을 `diff -rq`로 확인(차이 없음).
3. venv에 lock대로 Pillow 12.3.0만 설치. Python 3.13.18.
4. v1.0 `tools/qa_runner.py` **31/31 OK**, v1.3 `unittest` **19/19 OK**, `doctor.py` exit 0.
5. 읽기 전용 probe(`00_SESSION/evidence/p00_interface_probe.py`)로 실제 함수 시그니처를 추출하고 결함 11개 항목을 재현·확인했다.
6. 실제 인터페이스 매핑과 P01 수정 파일·인수 기준을 확정했다: `docs/P00_INTERFACE_MAP.md`.

## 변경·추가 파일
- 추가: `docs/P00_INTERFACE_MAP.md`, `00_SESSION/evidence/*` (probe 코드·결과·로그), `RELEASE_MANIFEST_P00.json`, `tools/verify_release.py`
- 갱신: `00_SESSION/PHASE_STATUS.json`, `TEST_RESULTS.json`, `OPEN_ISSUES.md`, `DECISIONS.md`(추가만), 이 파일
- 보존: `reference/originals/*`, `ARTIFACT_MANIFEST.json`(원본 인계 기준. 갱신 후 `verify_handoff.py`는 00_SESSION 해시 불일치를 보고하는 것이 정상이며, 새 기준은 `tools/verify_release.py`)

## 재현 명령 (Linux)
```bash
cd workspace/Naver_Blog_Automation && python3 -m venv .venv && .venv/bin/pip install -r tools/dependencies.lock
.venv/bin/python tools/qa_runner.py
cd 11_ADDONS/DANAWA_SNAPSHOT_PROBE && ../../.venv/bin/python -m unittest discover -s tests -v
cd ../../../.. && workspace/Naver_Blog_Automation/.venv/bin/python 00_SESSION/evidence/p00_interface_probe.py
python3 tools/verify_release.py
```

## 핵심 발견
- **I02 재현:** meta `shipping_fee=0`이 A·B·C 모두에 적용된다. 그 결과 카드 전용 C(80,000원)가 단순 최저가로 선택된다.
- **I03:** v1.3 CSV 행을 v1.0에 그대로 넣으면 가격·URL·시각이 전부 사라진다(키 불일치).
- **I08:** v1.0 정규화가 증거 필드를 버린다. sidecar가 필요하다.
- v1.1/v1.2 원본은 여전히 없다(BLOCKED_INPUT). 추측 구현을 하지 않았다.

## 미검증 (수행하지 않음)
Windows BAT 실행, 실제 다나와 수집, 네이버쇼핑 수집, 네이버 게시, v1.0↔v1.3 E2E, 네이버 API 종료 공지 재확인.

## 다음 최소 목표 = P01 (자동 시작 금지)
`docs/P00_INTERFACE_MAP.md` §3의 파일 목록과 인수 기준 1~8을 그대로 수행한다.
필요 입력: 없음(합성 데이터로 진행). v1.1/v1.2 원본이 있으면 같이 올린다. 그러면 직접 어댑터 대신 원본 검사를 먼저 한다.
