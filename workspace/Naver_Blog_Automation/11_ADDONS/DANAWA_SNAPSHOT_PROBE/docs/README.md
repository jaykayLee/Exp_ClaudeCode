# Danawa Snapshot Probe v1.3 (2026-11-01)

## Scope
이번 단계는 수집 권한이 확인되지 않은 사이트를 자동 호출하지 않고, **사용자가 브라우저에서 저장한 HTML 1개**에 가격 후보가 구조화 데이터(`Product`/`Offer` JSON-LD)로 포함되어 있는지 판단하는 오프라인 점검기입니다.

- `run_demo.bat`: 합성 상품 데이터로 동작 확인 (`DEMO_ONLY` 강제)
- `run_snapshot.bat`: 사용자가 저장한 HTML과 직접 작성한 메타 JSON 검사
- `smoke.bat`: Python unittest
- `doctor.bat`: Python 탐지, v1.0/v1.2 위치 진단
- `install.bat`: 별도 코어 덮어쓰기 없이 `11_ADDONS/DANAWA_SNAPSHOT_PROBE`에 설치
- `open_guide.bat`: 정적 한국어 HTML 안내

## 중요한 한계
1. **실시간 다나와 스크래핑 구현이 아닙니다.** 네트워크 요청이 없습니다. 브라우저 자동화/로그인/우회 기능도 없습니다.
2. **다나와 실제 HTML 구조 검증 전**입니다. JSON-LD가 없으면 `NO_STRUCTURED_OFFERS`를 반환합니다. 보이는 가격 텍스트에서 임의 숫자를 추측해 선택하지 않습니다.
3. HTML을 저장한 시각은 가격을 확인한 정확한 시각과 다를 수 있습니다. 확인시각과 배송비·결제조건은 사용자가 직접 증빙하고 기록해야 합니다.
4. `usage_permission="confirmed"`는 사용자의 입력 선언일 뿐 권리 이용 가능성에 대한 법률적 보증이 아닙니다.
5. 실제 출력 CSV가 **v1.2의 열 이름을 기준**으로 구성됐지만, 기존 v1.2 ZIP의 실행 바이너리를 이번 실행 환경에서 재료화하지 못했기 때문에 **실제 v1.2 통합 테스트는 수행하지 못했습니다.**
6. `candidates_for_review.csv`는 *검토용*이며 자동 블로그 게시나 최저가 표시를 허가하지 않습니다. `AggregateOffer.lowPrice`는 실제 구매 가능한 개별 Offer가 아니므로 CSV에 넣지 않습니다.

## 사용 순서
1. 원본 v1.0의 `install.bat` 및 `doctor.bat`에서 Windows 환경이 정상인지 검사합니다.
2. 이 Add-on을 같은 상위 폴더에 압축 해제하고 `install.bat` 실행. 독립적으로 테스트만 할 때는 설치하지 않아도 됩니다.
3. `run_demo.bat` 후 `output/demo/snapshot_report.html`을 열어 `DEMO_ONLY` 확인.
4. 개인적으로 저장한 HTML (`.html`)을 준비하고 `fixtures/manual_meta_template.json`을 복사해 값을 정확히 기입합니다. HTML 보관·재이용 권한도 별도로 확인합니다.
5. `run_snapshot.bat`를 통해 HTML·메타 JSON 경로를 입력합니다. `output/manual/`에 JSON/HTML/CSV 보고서가 생성됩니다.
6. 실제 후보 검토 CSV가 생겼다면 v1.2 템플릿 필드 및 `Danawa Candidate QA v1.1`의 모델·옵션·가격 검증이 성공하는지 **수동으로 테스트**합니다. 통합 실패 시 기존 파일을 바꾸지 않고 별도 오류 기록을 남깁니다.

## CLI
```bat
py -3 -m probe.snapshot_probe demo --out output\demo
py -3 -m probe.snapshot_probe inspect --html C:\evidence\product.html --meta C:\evidence\meta.json --out output\manual
py -3 -m unittest discover -s tests -v
```

## 출력 상태
- `DEMO_ONLY`: 합성 데이터, CSV 상품 행 미출력
- `NO_STRUCTURED_OFFERS`: JSON-LD Product/Offer가 없는 상태, CSV 상품 행 미출력
- `HOLD_REVIEW`: 후보 구조는 있으나 가격·권한·옵션·시간 등에 미확인 항목 존재
- `REVIEW_CANDIDATES_AVAILABLE`: 입력 조건을 만족한 후보가 검토용 CSV에 기록됨. 사람이 추가 검토해야 함

## 다음에 할 일
- 실제 저장 HTML 1개에서 JSON-LD Product/Offer 유무·항목 매핑 확인.
- 확인된 자료 제공·이용 권한 범위에서 API/공식 파일 내보내기 등 공급 경로 결정.
- 기존 v1.2 CSV Bridge의 실제 입력 스키마와 v1.3 출력 대조 후 1상품/3후보 통합 검사.
- 그 다음 네이버쇼핑 가격 소스의 허용된 대체 경로 결정.

## 확인할 공식 자료
- 다나와 이용약관: https://m.danawa.com/info/useTerms.html (2026-07-13 시행 표기, 2026-11-01 확인)
- 네이버 쇼핑 검색 API 2026-07-31 종료: https://developers.naver.com/notice/article/32564
- NAVER API HUB 이관과 쇼핑 제외: https://developers.naver.com/notice/article/32530
