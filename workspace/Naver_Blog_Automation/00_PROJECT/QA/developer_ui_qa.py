from pathlib import Path
import sys,json,threading,tempfile,shutil,http.client
PROJECT_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PROJECT_ROOT/'tools'))
from environment import ROOT
from server import LocalServer
from playwright.sync_api import sync_playwright
OUT=PROJECT_ROOT/'09_LOGS/ui_developer_qa';OUT.mkdir(parents=True,exist_ok=True)
checks=[];errors=[]
def ok(name):checks.append({'name':name,'passed':True})
with tempfile.TemporaryDirectory(prefix='nb_ui_qa_') as temp:
    root=Path(temp)/'Naver_Blog_Automation';shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    server=LocalServer(('127.0.0.1',0),root);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            import os;exe=next((x for x in ('/usr/bin/chromium','/opt/pw-browsers/chromium') if os.path.exists(x)),None);browser=p.chromium.launch(executable_path=exe,headless=True,args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
            def bridge(path,options):
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                conn.request(options.get('method','GET'),path,body=options.get('body','').encode('utf-8') or None,headers=options.get('headers',{}))
                response=conn.getresponse();data={'status':response.status,'body':response.read().decode('utf-8')};conn.close();return data
            page.expose_function('localTestFetch',bridge)
            original_html=(root/'06_UI/index.html').read_text(encoding='utf-8')
            test_html=original_html.replace("if(location.protocol!=='http:'||location.hostname!=='127.0.0.1')return;",'/* Test harness: actual HTTP transport is separately tested. */')
            test_html=test_html.replace('<script>',"<script>window.fetch=async(path,options={})=>{const r=await window.localTestFetch(path,options);return new Response(r.body,{status:r.status,headers:{'Content-Type':'application/json'}});};</script><script>",1)
            page.set_content(test_html,wait_until='load');page.wait_for_function("document.querySelector('#connection').textContent.includes('로컬 서버 연결')")
            ok('UI_connected_to_actual_local_HTTP_server_via_test_transport');page.screenshot(path=str(OUT/'desktop_overview.png'))
            page.locator('#demoButton').click();assert page.locator('#productRows tr').count()==3
            assert '123,400원' in page.locator('#productRows').inner_text();ok('demo_three_rows_and_price_format')
            page.locator('#runButton').click();page.wait_for_function("document.querySelector('#runStatus').textContent.includes('테스트 자료')")
            assert page.locator('.requiredtable th').all_inner_texts()==['No.','상품명','이미지','다나와 최저가','사이트 주소','네이버 최저가','사이트 주소'];ok('python_demo_generation_exact_seven_columns')
            page.locator('#workbench').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'desktop_workbench.png'))
            preview=context.new_page();preview_path=root/'08_OUTPUT/runs'/page.locator('#runStatus a[href$="product_table.html"]').get_attribute('href').removeprefix('/output/');preview.set_content(preview_path.read_text(encoding='utf-8'));assert 'DEMO_ONLY' in preview.inner_text('body');assert preview.locator('img').count()==3
            assert preview.evaluate('Array.from(document.images).every(i=>i.complete&&i.naturalWidth===354&&i.naturalHeight===472)');ok('output_html_embedded_images_render');preview.close()
            page.locator('#clearButton').click();page.locator('#newButton').click()
            page.locator('[name=query]').fill('검증용 상품 <script>금지</script>');page.locator('[name=model]').fill('QA-MODEL-001')
            for source in ('danawa','naver'):
                page.locator(f'[name={source}_price]').fill('123400')
                page.locator(f'[name={source}_url]').fill('https://example.com/product')
                page.locator(f'[name={source}_condition]').fill('테스트 입력: 동일 조건, 실제 가격 아님')
            page.locator('#productRights').select_option('owned');page.locator('#productCredit').fill('프로젝트 생성 테스트 이미지')
            page.locator('#imageFile').set_input_files(str(root/'07_DATA/samples/portrait.png'))
            page.wait_for_function("document.querySelector('#imageUploadStatus').textContent.includes('원본 저장 완료')")
            page.locator('#productImagePath').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'product_modal.png'))
            page.locator('#productForm button[type=submit]').click();assert page.locator('#productRows script').count()==0;ok('product_modal_image_upload_and_html_escape')
            page.locator('#runButton').click();page.wait_for_function("document.querySelector('#runStatus').textContent.includes('검토 보류')");ok('manual_missing_checks_hold')
            page.locator('[data-edit="0"]').click()
            for source in ('danawa','naver'):
                page.locator(f'[data-now={source}]').click();page.locator(f'[name={source}_match_checked]').check();page.locator(f'[name={source}_terms_checked]').check()
            page.locator('#productForm button[type=submit]').click();page.locator('#runButton').click();page.wait_for_function("document.querySelector('#runStatus').textContent.includes('형식 검사 통과')");ok('manual_review_gate_not_publication')
            with page.expect_download() as event:page.locator('#exportButton').click()
            f=OUT/'qa_input.json';event.value.save_as(str(f));data=json.loads(f.read_text());assert data['mode']=='MANUAL_IMPORT';assert len(data['records'])==1;ok('json_export')
            page.locator('#clearButton').click();page.locator('#jsonFile').set_input_files(str(f));page.wait_for_function("document.querySelector('#rowCount').textContent.includes('1개')");ok('json_reimport')
            page.locator('#briefEvidence').fill('프로젝트 테스트: 실제 제품 구매·사용 경험은 없음.');page.locator('#makeBriefButton').click();text=page.locator('#briefOutput').input_value();assert '\n## 1.' in text;assert '실제 제품 구매' in text;assert '\\n##' not in text
            page.locator('#saveBriefButton').click();page.wait_for_function("document.querySelector('#toast').textContent.includes('저장 완료: 04_CONTENT')");ok('original_content_brief_generation_and_save')
            page.locator('#imgWidth').fill('413');page.locator('#saveImageButton').click();page.wait_for_function("document.querySelector('#toast').textContent.includes('이미지 설정 저장 완료')")
            cfg=json.loads((root/'01_CONFIG/settings.local.json').read_text());assert cfg['image']['width_px']==413;ok('image_config_persisted')
            assert not page.evaluate("document.documentElement.scrollWidth>innerWidth+1");ok('desktop_no_document_horizontal_overflow')
            missing=page.evaluate("Array.from(document.querySelectorAll('a[href^=\"#\"]')).filter(a=>!document.querySelector(a.getAttribute('href'))).map(a=>a.getAttribute('href'))");assert not missing;ok('all_internal_navigation_targets_exist')
            offline=context.new_page();offline.on('pageerror',lambda e:errors.append(str(e)));offline.set_content(original_html);assert offline.locator('#runButton').is_disabled();offline.locator('#demoButton').click();assert offline.locator('#productRows tr').count()==3;offline.locator('#makeBriefButton').click();assert '콘텐츠 브리프' in offline.locator('#briefOutput').input_value();ok('standalone_HTML_render_demo_and_brief_no_python')
            mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,device_scale_factor=1)
            m=mobile.new_page();m.on('pageerror',lambda e:errors.append(str(e)));m.set_content(original_html);m.screenshot(path=str(OUT/'mobile_overview.png'))
            assert not m.evaluate('document.documentElement.scrollWidth>innerWidth+1');m.locator('#mobileMenu').click();m.locator('.sidebar a[href="#workbench"]').click();assert not m.locator('#sidebar').is_visible();m.locator('#demoButton').click();assert m.locator('#productRows tr').count()==3;ok('mobile_navigation_and_horizontal_table_scroll')
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
assert not errors,errors
result={'browser':'Chromium / Playwright on Linux; set_content rendering; browser navigation restricted by container policy; UI API calls use an explicit test bridge to the actual local HTTP server','checks':checks,'passed':len(checks),'javascript_errors':errors,'windows_browser_tested':False,'live_price_collection_tested':False,'public_posting_tested':False}
(OUT/'ui_test_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
