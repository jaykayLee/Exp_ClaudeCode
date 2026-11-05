# v1.3.1 — 2026-11-05 (P01)

v1.3.0의 원래 코드를 바탕으로 한 최소 수정이다. 누락된 v1.1/v1.2의 재현이 아니다.

## 변경
- `offer_candidates`: Offer 단위 `seller`(이름·@id), `shippingDetails.shippingRate`(KRW, 단일 요금만), 조건부 가격 문구(카드·렌탈·약정·쿠폰·할부·월 납입 등)를 후보에 보존한다.
- `inspect_snapshot`
  - 배송비는 ① meta `offer_terms`의 URL별 기록, ② Offer JSON-LD 순서로 판단한다. 두 값이 다르면 `SHIPPING_EVIDENCE_CONFLICT`로 보류한다.
  - 최상위 meta `shipping_fee`·`payment_condition`은 `offer_terms_scope: "all_offers"`를 명시한 경우에만 모든 후보에 적용한다. 명시가 없으면 적용하지 않고 `META_TERMS_NOT_APPLIED_SCOPE_UNDECLARED` 경고를 남긴다.
  - 조건부 문구가 있으면 `PAYMENT_CONDITIONAL_HINT`로 보류한다. 사용자가 normal로 기록했어도 보류한다.
  - 같은 URL의 offer_terms가 중복되면 `OFFER_TERMS_AMBIGUOUS`로 보류한다.
  - 보고서 후보에 `offer_index, seller_name, seller_id, currency, product_condition, shipping_fee, shipping_source, payment_condition, payment_source, payment_hints`를 추가했다. 기존 키는 유지했다.
  - `fresh_hours` 인자(1~168, 기본 24)로 v1.0 설정값을 전달할 수 있다.
- CSV 열(`CSV_COLUMNS`)과 DEMO에서 CSV 0건 계약은 바뀌지 않았다.

## 의도적 계약 변경
- 기존 테스트 `BASE` meta에 `offer_terms_scope: "all_offers"` 1줄을 추가했다. 이전 동작(공통 meta를 모든 판매자 사실로 승격)은 카드 전용 후보를 최저가로 오선택하게 했다(P00 재현).
- 데모 fixture(`demo_meta.json`)는 수정하지 않았다. 범위 선언이 없으므로 이제 배송비·결제조건이 미확인으로 표시된다. DEMO라서 CSV는 원래대로 0건이다.

## 검증 (Linux, Python 3.13.18)
- `python -m unittest discover -s tests -v`: 26 실행 / 0 실패 (기존 19 + 신규 7)
- `python -m probe.snapshot_probe demo`: DEMO_ONLY, 후보 2, CSV 0
- Windows BAT 실행, 실제 다나와 HTML: 미검증
