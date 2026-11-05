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

if __name__=='__main__': unittest.main()
