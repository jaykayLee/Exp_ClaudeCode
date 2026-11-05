from __future__ import annotations
import base64
import copy
import hashlib
import http.client
import json
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
from environment import ROOT
from nbcore.config import load_config,save_image_config
from nbcore.validation import normalize_price,public_link,normalize_records,review_issues,now_kst
from nbcore.images import store_original,resize_product_image,inspect_image,validate_download_url,download_image,ImageError
from nbcore.pipeline import run_pipeline,pipeline_lock
from exporters.table_exporter import render_product_table
from providers.danawa import DanawaProvider
from providers.naver_shopping import NaverShoppingProvider
from providers.base import ProviderUnavailable
from publishers.naver import NaverPublisher
from server import LocalServer

class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='blog_workspace_')
        self.root=Path(self.tmp.name)
        for folder in ('01_CONFIG','06_UI','07_DATA/samples','04_CONTENT'):
            (self.root/folder).mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'01_CONFIG/settings.example.json',self.root/'01_CONFIG/settings.example.json')
        for file in (ROOT/'07_DATA/samples').iterdir():
            if file.is_file():shutil.copyfile(file,self.root/'07_DATA/samples'/file.name)
        (self.root/'06_UI/index.html').write_text('<!doctype html><title>Test</title>',encoding='utf-8')
        self.config=load_config(self.root)
        self.rows=json.loads((self.root/'07_DATA/samples/products_demo.json').read_text(encoding='utf-8'))['records']
    def tearDown(self):self.tmp.cleanup()
    def valid_row(self):
        row=copy.deepcopy(self.rows[0])
        for source in ('danawa','naver'):
            row[source+'_observed_at']=now_kst().isoformat()
            row[source+'_match_checked']=True
            row[source+'_terms_checked']=True
            row[source+'_condition']='동일 모델/새 상품/배송비 포함/쿠폰 없음 (테스트 입력)'
        return row

class ValidationTests(WorkspaceCase):
    def test_single_price_only(self):
        for value in ('123,400원','  ₩123,400 ',123400):self.assertEqual(normalize_price(value),123400)
        for value in (None,True,False,0,-1,'0원','10,000~20,000원','월 9,900원','정가 12000 할인 9900','12,34원','1'*100):
            self.assertIsNone(normalize_price(value),repr(value))
    def test_links(self):
        self.assertEqual(public_link('https://example.com/item?id=1'),'https://example.com/item?id=1')
        for url in ('javascript:alert(1)','file:///c:/x','https://user:pw@example.com/','http://127.0.0.1','http://192.168.0.1','http://localhost:8000','http://example.com\n/a'):
            self.assertIsNone(public_link(url),url)
    def test_bounds(self):
        for rows in ([],[{}],[{'query':'a'}]*31,'x'):
            with self.assertRaises(ValueError):normalize_records(rows)
    def test_stale_future_and_missing_timestamps(self):
        row=normalize_records([self.valid_row()])[0]
        self.assertEqual(review_issues(row),[])
        row['danawa_observed_at']=(now_kst()-timedelta(hours=25)).isoformat()
        self.assertIn('danawa:STALE_PRICE',review_issues(row))
        row['danawa_observed_at']=(now_kst()+timedelta(hours=1)).isoformat()
        self.assertIn('danawa:FUTURE_TIMESTAMP',review_issues(row))
        row['danawa_observed_at']='2026-10-11T08:00:00'
        self.assertIn('danawa:TIMESTAMP_REQUIRED',review_issues(row))
    def test_true_boolean_and_condition_required(self):
        row=self.valid_row();row['danawa_match_checked']='true';row['naver_condition']=''
        issues=review_issues(normalize_records([row])[0])
        self.assertIn('danawa:MATCH_NOT_REVIEWED',issues)
        self.assertIn('naver:CONDITION_REQUIRED',issues)
    def test_price_error_preserved(self):
        row=self.valid_row();row['naver_price']='9900 / 19000'
        self.assertIn('naver:INVALID_PRICE',normalize_records([row])[0]['input_issues'])
    def test_config_safe_and_reinstallation_preserves_config(self):
        save_image_config(self.root,{'width_px':413})
        self.assertEqual(load_config(self.root)['image']['width_px'],413)
        for change in ({'width_px':2},{'dpi':True},{'allowed_hosts':['*.example.com']},{'auto_publish':True}):
            with self.assertRaises(ValueError):save_image_config(self.root,change)
    def test_credit_needed_for_permission(self):
        row=self.valid_row();row['image_rights']='permission';row['image_credit']=''
        self.assertIn('IMAGE_CREDIT_REQUIRED',review_issues(normalize_records([row])[0]))

class ImageTests(WorkspaceCase):
    def test_three_aspect_ratios_and_original_integrity(self):
        for name in ('landscape.png','portrait.png','transparent.png'):
            source=self.root/'07_DATA/samples'/name;before=hashlib.sha256(source.read_bytes()).hexdigest()
            relative=resize_product_image(self.root,'07_DATA/samples/'+name)
            with Image.open(self.root/relative) as img:
                self.assertEqual(img.size,(354,472));self.assertEqual(img.mode,'RGB')
                self.assertGreaterEqual(min(img.getpixel((0,0))),245)
                self.assertAlmostEqual(img.info['dpi'][0],300,delta=1)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
    def test_original_import_hash_and_evidence(self):
        data=(self.root/'07_DATA/samples/landscape.png').read_bytes()
        result=store_original(self.root,data,'owned',credit='테스트 생성물')
        self.assertTrue((self.root/result).exists())
        evidence=json.loads((self.root/result).with_suffix('.png.json').read_text(encoding='utf-8'))
        self.assertFalse(evidence['legal_rights_verified_by_software'])
        self.assertEqual(evidence['sha256'],hashlib.sha256(data).hexdigest())
    def test_bad_image_and_rights(self):
        with self.assertRaises(ImageError):inspect_image(b'<html>not image</html>')
        with self.assertRaises(ImageError):store_original(self.root,b'x','unknown')
        data=(self.root/'07_DATA/samples/landscape.png').read_bytes()
        with self.assertRaises(ImageError):inspect_image(data,max_pixels=10)
    def test_path_traversal_and_dimensions(self):
        with self.assertRaises(ImageError):resize_product_image(self.root,'../secret.jpg')
        with self.assertRaises(ImageError):resize_product_image(self.root,'07_DATA/samples/landscape.png',5,5)
    def test_download_default_off_and_host_allowlist(self):
        with self.assertRaisesRegex(ImageError,'DISABLED'):download_image(self.root,'https://example.com/a.jpg',self.config['image'],'owned')
        with self.assertRaisesRegex(ImageError,'HOST_NOT_ALLOWED'):validate_download_url('https://evil.example/a.jpg',['example.com'])
    def test_private_and_mixed_dns_are_rejected(self):
        answers=[(2,1,6,'',('127.0.0.1',443))]
        with patch('nbcore.images.socket.getaddrinfo',return_value=answers):
            with self.assertRaisesRegex(ImageError,'PRIVATE_NETWORK'):validate_download_url('https://example.com/a.jpg',['example.com'])
        answers.append((2,1,6,'',('1.1.1.1',443)))
        with patch('nbcore.images.socket.getaddrinfo',return_value=answers):
            with self.assertRaises(ImageError):validate_download_url('https://example.com/a.jpg',['example.com'])
    def test_public_ip_is_pinned(self):
        with patch('nbcore.images.socket.getaddrinfo',return_value=[(2,1,6,'',('1.1.1.1',443))]):
            self.assertEqual(validate_download_url('https://example.com/a.jpg?q=1',['example.com']),('example.com','1.1.1.1','/a.jpg?q=1'))
    def test_http_429_stops_without_retry(self):
        settings={**self.config['image'],'download_enabled':True,'allowed_hosts':['example.com']}
        with patch('nbcore.images.validate_download_url',return_value=('example.com','1.1.1.1','/a')) as check, patch('nbcore.images._PinnedHTTPSConnection') as connection:
            connection.return_value.getresponse.return_value.status=429
            with self.assertRaisesRegex(ImageError,'HTTP_429'):download_image(self.root,'https://example.com/a',settings,'owned')
            self.assertEqual(check.call_count,1);self.assertEqual(connection.call_count,1)
    def test_mock_download_stores_valid_image(self):
        settings={**self.config['image'],'download_enabled':True,'allowed_hosts':['example.com']}
        with patch('nbcore.images.validate_download_url',return_value=('example.com','1.1.1.1','/a')), patch('nbcore.images._PinnedHTTPSConnection') as c:
            response=c.return_value.getresponse.return_value;response.status=200
            response.getheader.return_value='image/png';response.read.return_value=(self.root/'07_DATA/samples/portrait.png').read_bytes()
            result=download_image(self.root,'https://example.com/a',settings,'owned')
            self.assertTrue((self.root/result).exists())

class TableParser(HTMLParser):
    def __init__(self):super().__init__();self.headers=[];self.in_th=False;self.in_tbody=False;self.counts=[];self.cells=0
    def handle_starttag(self,tag,attrs):
        if tag=='th':self.in_th=True
        if tag=='tbody':self.in_tbody=True
        if tag=='tr' and self.in_tbody:self.cells=0
        if tag=='td' and self.in_tbody:self.cells+=1
    def handle_data(self,data):
        if self.in_th:self.headers.append(data)
    def handle_endtag(self,tag):
        if tag=='th':self.in_th=False
        if tag=='tr' and self.in_tbody:self.counts.append(self.cells)
        if tag=='tbody':self.in_tbody=False

class PipelineTests(WorkspaceCase):
    def test_demo_seven_columns_and_three_images(self):
        result=run_pipeline(self.root,self.rows,'DEMO');self.assertEqual(result['review_gate'],'DEMO_ONLY');self.assertFalse(result['published'])
        output=self.root/result['output_relative'];p=TableParser();p.feed((output/'product_table.html').read_text(encoding='utf-8'))
        self.assertEqual(p.headers,['No.','상품명','이미지','다나와 최저가','사이트 주소','네이버 최저가','사이트 주소'])
        self.assertEqual(p.counts,[7,7,7]);self.assertEqual(len(list((output/'images').glob('*.jpg'))),3)
    def test_ready_means_only_manual_review(self):
        result=run_pipeline(self.root,[self.valid_row()]);self.assertEqual(result['review_gate'],'READY_FOR_MANUAL_REVIEW');self.assertFalse(result['published']);self.assertFalse(result['network_price_collection'])
    def test_missing_source_keeps_row_and_holds(self):
        row=self.valid_row();row['naver_price']=None
        result=run_pipeline(self.root,[row]);self.assertEqual(result['row_count'],1);self.assertEqual(result['review_gate'],'HOLD')
    def test_bad_image_keeps_prices(self):
        row=self.valid_row();row['image_path']='07_DATA/samples/missing.png'
        result=run_pipeline(self.root,[row]);data=json.loads((self.root/result['output_relative']/'normalized_products.json').read_text(encoding='utf-8'))
        self.assertEqual(data[0]['danawa_price'],123400);self.assertIsNone(data[0]['image_path']);self.assertEqual(result['review_gate'],'HOLD')
    def test_repeat_same_input_does_not_fake_price_timestamp(self):
        row=self.valid_row();a=run_pipeline(self.root,[row]);b=run_pipeline(self.root,[row])
        self.assertEqual(a['run_id'],b['run_id']);self.assertTrue(b['reused_output'])
        saved=json.loads((self.root/b['output_relative']/'normalized_products.json').read_text(encoding='utf-8'))
        self.assertEqual(saved[0]['danawa_observed_at'],row['danawa_observed_at'])
    def test_lock_prevents_parallel_write_and_cleans_up(self):
        with pipeline_lock(self.root):
            with self.assertRaisesRegex(ValueError,'PIPELINE_BUSY'):run_pipeline(self.root,self.rows,'DEMO')
        self.assertFalse((self.root/'07_DATA/state/pipeline.lock').exists())
    def test_stale_generated_image_removed_on_later_failure(self):
        row=self.valid_row();first=run_pipeline(self.root,[row]);output=self.root/first['output_relative']
        (self.root/row['image_path']).unlink();second=run_pipeline(self.root,[row])
        self.assertEqual(first['run_id'],second['run_id']);self.assertFalse((output/'images/product_01.jpg').exists())
    def test_html_escapes_untrusted_text(self):
        row=self.valid_row();row['query']='<script>alert(1)</script>';row['danawa_url']='javascript:alert(1)'
        result=run_pipeline(self.root,[row]);text=(self.root/result['output_relative']/'product_table.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>alert(1)</script>',text);self.assertIn('&lt;script&gt;',text);self.assertNotIn('href="javascript:',text)
    def test_live_and_publishing_are_explicitly_unavailable(self):
        for cls in (DanawaProvider,NaverShoppingProvider):
            with self.assertRaises(ProviderUnavailable):cls().collect('TEST','')
        with self.assertRaises(NotImplementedError):NaverPublisher().publish({}, {})

class HTTPTests(WorkspaceCase):
    def setUp(self):
        super().setUp();self.server=LocalServer(('127.0.0.1',0),self.root)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2);super().tearDown()
    def request(self,method,path,data=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=8)
        blob=json.dumps(data).encode() if data is not None else None
        conn.request(method,path,body=blob,headers=headers or {});response=conn.getresponse();result=(response.status,response.read());conn.close();return result
    def test_status_and_missing_secret_routes(self):
        code,data=self.request('GET','/api/status');self.assertEqual(code,200);self.assertFalse(json.loads(data)['auto_publish'])
        self.assertEqual(self.request('GET','/01_CONFIG/settings.local.json')[0],404)
        self.assertEqual(self.request('GET','/output/../../01_CONFIG/settings.local.json')[0],404)
    def test_host_and_origin_guard(self):
        self.assertEqual(self.request('GET','/api/status',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('GET','/api/status',headers={'Origin':'https://evil.example'})[0],403)
    def test_mutation_requires_token(self):
        self.assertEqual(self.request('POST','/api/run',{'records':self.rows,'mode':'DEMO'},{'Content-Type':'application/json'})[0],403)
    def test_demo_api_and_output(self):
        headers={'Content-Type':'application/json','X-Workspace-Token':self.server.token}
        code,data=self.request('POST','/api/run',{'records':self.rows,'mode':'DEMO'},headers);self.assertEqual(code,200)
        result=json.loads(data);self.assertEqual(result['review_gate'],'DEMO_ONLY');self.assertEqual(self.request('GET',result['preview_url'])[0],200)
    def test_local_image_upload_and_brief_save(self):
        headers={'Content-Type':'application/json','X-Workspace-Token':self.server.token}
        raw=(self.root/'07_DATA/samples/portrait.png').read_bytes()
        code,_=self.request('POST','/api/image',{'data':base64.b64encode(raw).decode(),'rights':'owned'},headers);self.assertEqual(code,200)
        code,data=self.request('POST','/api/brief',{'text':'# 원본 브리프\n검토 필요'},headers);self.assertEqual(code,200);self.assertTrue((self.root/json.loads(data)['saved']).exists())

if __name__=='__main__':unittest.main()
