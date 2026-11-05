import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta

from probe.snapshot_probe import (
    inspect_snapshot, read_jsonld, offer_candidates, krw_int, safe_https_url,
    aware_date, save_report, CSV_COLUMNS, render_html,
)

NOW = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
HTML = b'''<script type="application/ld+json">{
  "@context":"https://schema.org","@type":"Product","name":"DEMO",
  "model":"TEST-1","color":"black","offers":[
    {"@type":"Offer","price":123000,"priceCurrency":"KRW",
      "url":"https://example.com/item","itemCondition":"https://schema.org/NewCondition"},
    {"@type":"AggregateOffer","lowPrice":1,"highPrice":2}
  ]}</script>'''
BASE = {
    'target': {'query':'DEMO','model':'TEST-1','variant':'black'},
    'source_page':'https://prod.danawa.com/info/?pcode=123',
    'observed_at':'2026-11-01T08:00:00+09:00',
    'usage_permission':'confirmed',
    'shipping_fee':0,
    'payment_condition':'normal',
    # v1.3.1 contract change (P01, DECISIONS.md): meta terms apply to every offer only when declared.
    'offer_terms_scope':'all_offers',
}


class TestProbe(unittest.TestCase):
    def report(self, html_bytes=HTML, meta=None):
        return inspect_snapshot(html_bytes, BASE if meta is None else meta, now=NOW)

    def test_offer_and_aggregate(self):
        r=self.report()
        self.assertEqual(r['candidate_count'],1)
        self.assertIn('AGGREGATE_OFFER_SKIPPED',r['warnings'])

    def test_review_row_generated(self):
        r=self.report()
        self.assertEqual(r['status'],'REVIEW_CANDIDATES_AVAILABLE')
        self.assertEqual(r['review_csv_count'],1)
        self.assertEqual(r['_csv_rows'][0]['base_price'],123000)

    def test_permission_required(self):
        meta={**BASE,'usage_permission':'unknown'}
        r=self.report(meta=meta)
        self.assertEqual(r['status'],'HOLD_REVIEW')
        self.assertIn('SOURCE_PERMISSION_UNCONFIRMED',r['candidates'][0]['issues'])

    def test_stale_blocks(self):
        meta={**BASE,'observed_at':'2026-10-29T08:00:00+09:00'}
        r=self.report(meta=meta)
        self.assertEqual(r['review_csv_count'],0)
        self.assertIn('OBSERVED_AT_OUTSIDE_24H',r['candidates'][0]['issues'])

    def test_unknown_shipping_blocks(self):
        meta={**BASE,'shipping_fee':None}
        self.assertIn('SHIPPING_UNVERIFIED',self.report(meta=meta)['candidates'][0]['issues'])

    def test_boolean_shipping_rejected(self):
        meta={**BASE,'shipping_fee':False}
        self.assertIn('SHIPPING_UNVERIFIED',self.report(meta=meta)['candidates'][0]['issues'])

    def test_unknown_payment_blocks(self):
        meta={**BASE,'payment_condition':'unknown'}
        self.assertIn('PAYMENT_NOT_CONFIRMED_NORMAL',self.report(meta=meta)['candidates'][0]['issues'])

    def test_wrong_model_blocks(self):
        meta={**BASE,'target':{'query':'DEMO','model':'OTHER','variant':'black'}}
        self.assertIn('MODEL_NOT_VERIFIED_EQUAL',self.report(meta=meta)['candidates'][0]['issues'])

    def test_wrong_variant_blocks(self):
        meta={**BASE,'target':{'query':'DEMO','model':'TEST-1','variant':'white'}}
        self.assertIn('VARIANT_NOT_VERIFIED_EQUAL',self.report(meta=meta)['candidates'][0]['issues'])

    def test_plain_html_does_not_guess_prices(self):
        r=self.report(html_bytes=b'<h1>123,000 won &lt;script&gt;</h1>')
        self.assertEqual(r['status'],'NO_STRUCTURED_OFFERS')
        self.assertEqual(r['review_csv_count'],0)

    def test_invalid_jsonld(self):
        products,w=read_jsonld('<script type="application/ld+json">{broken</script>')
        self.assertEqual(products,[])
        self.assertIn('JSONLD_INVALID:0',w)

    def test_graph(self):
        products,w=read_jsonld('<script type="application/ld+json">{"@graph":[{"@type":"BreadcrumbList"},{"@type":"Product","name":"x"}]}</script>')
        self.assertEqual(len(products),1)

    def test_krw_parse_strict(self):
        self.assertEqual(krw_int('123,400'),123400)
        for val in ('월 12,000원', '50~100', '1.5', -10, 0, None, True):
            self.assertIsNone(krw_int(val))

    def test_host_check(self):
        self.assertTrue(safe_https_url('https://prod.danawa.com/info/?pcode=10',danawa_only=True))
        for url in ('http://danawa.com', 'https://danawa.com.evil.test', 'https://127.0.0.1/', 'file:///C:/x', 'https://user:password@danawa.com/'):
            self.assertFalse(safe_https_url(url,danawa_only=True))

    def test_timezone_required(self):
        self.assertIsNone(aware_date('2026-11-01T09:00:00'))
        self.assertIsNotNone(aware_date('2026-11-01T09:00:00+09:00'))

    def test_html_escaped(self):
        html_bad = HTML.replace(b'"DEMO"', b'"<img src=x onerror=alert(1)>"')
        output=render_html(self.report(html_bytes=html_bad))
        self.assertNotIn('<img src=x onerror=alert(1)>',output)
        self.assertIn('&lt;img',output)

    def test_saves_reports(self):
        with tempfile.TemporaryDirectory() as p:
            paths=save_report(self.report(),Path(p))
            self.assertTrue(Path(paths['csv']).exists())
            self.assertTrue(Path(paths['html']).exists())
            self.assertTrue(Path(paths['json']).exists())
            self.assertEqual(Path(paths['csv']).read_text(encoding='utf-8-sig').splitlines()[0].split(','),CSV_COLUMNS)

    def test_demo_always_not_exported(self):
        r=inspect_snapshot(HTML,BASE,now=NOW,demo=True)
        self.assertEqual(r['review_csv_count'],0)
        self.assertIn('DEMO_ONLY',r['candidates'][0]['issues'])

    def test_large_input_fails(self):
        with self.assertRaises(ValueError):
            self.report(html_bytes=b'x'*(5*1024*1024+1))

def _offer(price, url, **extra):
    o = {"@type": "Offer", "price": str(price), "priceCurrency": "KRW", "url": url,
         "itemCondition": "https://schema.org/NewCondition"}
    o.update(extra)
    return o


def _ship(value):
    return {"@type": "OfferShippingDetails", "shippingRate": {"value": value, "currency": "KRW"}}


def _html(*offers):
    import json
    p = {"@context": "https://schema.org", "@type": "Product", "name": "DEMO", "model": "TEST-1",
         "color": "black", "offers": list(offers)}
    return ('<script type="application/ld+json">' + json.dumps(p, ensure_ascii=False) + '</script>').encode()


ABC = _html(
    _offer(119000, "https://example.com/A", seller={"@type": "Organization", "name": "A"}, shippingDetails=_ship(0)),
    _offer(117000, "https://example.com/B", seller={"@type": "Organization", "name": "B"}, shippingDetails=_ship(5000)),
    _offer(80000, "https://example.com/C", seller={"@type": "Organization", "name": "C"}, description="카드 전용 할인가"),
)
LEGACY = {k: v for k, v in BASE.items() if k != 'offer_terms_scope'}


class TestPerOfferTerms(unittest.TestCase):
    """v1.3.1 regression: per-offer shipping/payment (OPEN_ISSUES I02)."""

    def test_meta_terms_without_scope_not_promoted(self):
        r = inspect_snapshot(HTML, LEGACY, now=NOW)
        self.assertEqual(r['review_csv_count'], 0)
        c = r['candidates'][0]
        self.assertIn('SHIPPING_UNVERIFIED', c['issues'])
        self.assertIn('PAYMENT_NOT_CONFIRMED_NORMAL', c['issues'])
        self.assertEqual(c['shipping_source'], 'none')
        self.assertIn('META_TERMS_NOT_APPLIED_SCOPE_UNDECLARED', r['warnings'])

    def test_offer_level_shipping_and_seller_kept(self):
        terms = [{"url": "https://example.com/A", "payment_condition": "normal"},
                 {"url": "https://example.com/B", "payment_condition": "normal"},
                 {"url": "https://example.com/C", "payment_condition": "card_only"}]
        r = inspect_snapshot(ABC, {**LEGACY, 'offer_terms': terms}, now=NOW)
        by = {c['seller_name']: c for c in r['candidates']}
        self.assertEqual((by['A']['shipping_fee'], by['A']['shipping_source']), (0, 'offer_jsonld'))
        self.assertEqual(by['B']['shipping_fee'], 5000)
        self.assertIsNone(by['C']['shipping_fee'])
        self.assertTrue(by['A']['eligible_for_review_csv'])
        self.assertTrue(by['B']['eligible_for_review_csv'])
        self.assertFalse(by['C']['eligible_for_review_csv'])
        self.assertIn('PAYMENT_NOT_CONFIRMED_NORMAL', by['C']['issues'])
        self.assertIn('PAYMENT_CONDITIONAL_HINT', by['C']['issues'])
        self.assertIn('SHIPPING_UNVERIFIED', by['C']['issues'])
        rows = {row['url']: row for row in r['_csv_rows']}
        self.assertEqual(rows['https://example.com/B']['shipping_fee'], 5000)

    def test_conditional_hint_blocks_even_if_declared_normal(self):
        terms = [{"url": "https://example.com/C", "payment_condition": "normal", "shipping_fee": 0}]
        r = inspect_snapshot(ABC, {**LEGACY, 'offer_terms': terms}, now=NOW)
        c = [x for x in r['candidates'] if x['url'].endswith('/C')][0]
        self.assertIn('PAYMENT_CONDITIONAL_HINT', c['issues'])
        self.assertFalse(c['eligible_for_review_csv'])

    def test_shipping_conflict_between_sources(self):
        terms = [{"url": "https://example.com/A", "payment_condition": "normal", "shipping_fee": 2500}]
        r = inspect_snapshot(ABC, {**LEGACY, 'offer_terms': terms}, now=NOW)
        a = [x for x in r['candidates'] if x['url'].endswith('/A')][0]
        self.assertIsNone(a['shipping_fee'])
        self.assertIn('SHIPPING_EVIDENCE_CONFLICT', a['issues'])

    def test_duplicate_offer_terms_ambiguous(self):
        terms = [{"url": "https://example.com/A", "payment_condition": "normal"},
                 {"url": "https://example.com/A", "payment_condition": "card_only"}]
        r = inspect_snapshot(ABC, {**LEGACY, 'offer_terms': terms}, now=NOW)
        a = [x for x in r['candidates'] if x['url'].endswith('/A')][0]
        self.assertIn('OFFER_TERMS_AMBIGUOUS', a['issues'])

    def test_multiple_or_bad_shipping_rates(self):
        bad = _html(_offer(1000, "https://example.com/X", shippingDetails=[_ship(0), _ship(3000)]),
                    _offer(1000, "https://example.com/Y", shippingDetails=_ship(True)),
                    _offer(1000, "https://example.com/Z", shippingDetails={"shippingRate": {"value": 10, "currency": "USD"}}))
        r = inspect_snapshot(bad, BASE, now=NOW)
        issues = {c['url'][-1]: c['issues'] for c in r['candidates']}
        self.assertIn('SHIPPING_MULTIPLE_OR_INVALID_RATES', issues['X'])
        self.assertIn('SHIPPING_RATE_INVALID', issues['Y'])
        self.assertIn('SHIPPING_CURRENCY_NOT_KRW', issues['Z'])
        for k in 'XYZ':
            self.assertIn('SHIPPING_UNVERIFIED', issues[k])

    def test_fresh_hours_parameter(self):
        meta = {**BASE, 'observed_at': '2026-10-30T09:00:00+09:00'}
        self.assertIn('OBSERVED_AT_OUTSIDE_24H', inspect_snapshot(HTML, meta, now=NOW)['candidates'][0]['issues'])
        self.assertNotIn('OBSERVED_AT_OUTSIDE_24H',
                         inspect_snapshot(HTML, meta, now=NOW, fresh_hours=72)['candidates'][0]['issues'])
        for bad in (0, 169, True, '24'):
            with self.assertRaises(ValueError):
                inspect_snapshot(HTML, meta, now=NOW, fresh_hours=bad)


if __name__=='__main__': unittest.main()
