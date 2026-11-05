# 인계 준비 감사 기록 — 2026-11-05

## 실제 확인한 범위

v1.0 원본 ZIP과 v1.3 원본 ZIP을 확보했고 CRC를 확인했다. 원본 파일은 변경하지 않았다. 독립 임시 사본에서 테스트를 재실행했다.

| 대상 | 명령 | 결과 | 환경 |
|---|---|---|---|
| v1.0 | 앱 root: python tools/qa_runner.py | 31 tests, 0 failures, 0 errors | Linux / Python 3.13.5 / Pillow 12.3.0 |
| v1.3 | Add-on root: python -m unittest discover -s tests -v | 19 tests, 0 failures, 0 errors | Linux / Python 3.13.5 |

전체 로그는 reference/verification에 있다. 외부 가격 사이트를 요청하지 않았다. v1.0은 loopback HTTP 검사를 포함한다.

## 현재 분류

| 기능 | 판단 |
|---|---|
| v1.0 로컬 표·이미지·입력 검토 | 코드 및 독립 회귀 검사 확인 |
| v1.3 저장 HTML JSON-LD 분석 | 코드 및 합성 회귀 검사 확인 |
| v1.1 / v1.2 | 원본 미확보, 이전 설명만으로 코드 상태 단정 불가 |
| v1.0↔v1.3 | 배치만 함, E2E 미검증 |
| 실제 Danawa HTML 구조 | 이번 인계 준비에서 미검증 |
| 실시간 가격 수집 | 기존 Provider는 명시적 unavailable, 구현 완료 아님 |
| 네이버 실제 게시 | 미구현/미검증 |
| Windows BAT 설치·예약 | 코드 포함, 실제 Windows 실행 미검증 |

## P01에 넘길 코드 발견 사항

1. v1.3의 inspect_snapshot은 meta 최상위 shipping_fee/payment_condition을 모든 개별 Offer에 공통 적용한다. 조건이 다른 판매자들의 가격을 선택할 때는 후보별 근거가 필요하다. 이는 코드 검토 결과이며 실제 판매 페이지에서 오류를 재현했다는 의미가 아니다.
2. v1.0 PriceCandidate는 provider, product_id, model, variant, price, url, observed_at, price_basis, image_url 필드이다. 후보 배송비·출처 hash 등의 richer evidence를 직접 담는 기존 인터페이스로 가정하면 안 된다.
3. v1.0 run_pipeline(root, records, mode)는 DEMO/MANUAL_IMPORT만 받는다. Snapshot 보고서는 이 입력과 같지 않다. 변환기와 테스트가 필요하다.
4. v1.3 DEMO_ONLY는 CSV 0행이 정상이다. 통합 데모를 위해 안전 게이트를 제거하지 않는다.
5. v1.0 정규화는 추가 필드를 그대로 보존한다고 보장하지 않는다. 후보 근거는 별도 sidecar에 보관하거나 검증된 스키마 확장으로 다룬다.

## 누락 원본 처리

v1.1/v1.2의 연결 호환성을 보증하지 않는다. 사용자의 원본 파일이 추가되면 검사하거나, 현재 가용한 두 모듈을 새 최소 어댑터로 직접 연결한다. 후자는 과거 모듈 복원본이 아니다.
