from __future__ import annotations
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, unquote
from pathlib import Path
import argparse
import base64
import binascii
import hashlib
import json
import mimetypes
import secrets
import threading
import webbrowser
from environment import ROOT
from nbcore.config import load_config, save_image_config
from nbcore.pipeline import run_pipeline, atomic_json
from nbcore.images import store_original

class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self, address, root=ROOT):
        self.root=root
        self.token=secrets.token_urlsafe(32)
        self.mutation_lock=threading.Lock()
        super().__init__(address,Handler)
    @property
    def authority(self):
        return f"127.0.0.1:{self.server_port}"

class Handler(BaseHTTPRequestHandler):
    server: LocalServer
    def log_message(self,format,*args):
        # Do not log bodies, image URLs or future credentials.
        print("[HTTP]", self.command, urlsplit(self.path).path, args[1] if len(args)>1 else "")
    def send_blob(self,status,data,mime):
        self.send_response(status)
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; frame-src 'self' blob:; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(data)
    def send_json(self,status,data):
        self.send_blob(status,json.dumps(data,ensure_ascii=False).encode('utf-8'),'application/json; charset=utf-8')
    def trusted(self,mutation=False):
        if self.headers.get("Host")!=self.server.authority:
            return False
        origin=self.headers.get("Origin")
        expected="http://"+self.server.authority
        if origin and origin!=expected:
            return False
        if mutation and self.headers.get("X-Workspace-Token")!=self.server.token:
            return False
        return True
    def do_GET(self):
        if not self.trusted():
            self.send_json(403,{"error":"LOCAL_ORIGIN_ONLY"});return
        root=self.server.root
        path=unquote(urlsplit(self.path).path)
        try:
            if path=="/api/status":
                cfg=load_config(root)
                latest=root/'07_DATA/state/latest_run.json'
                qa=root/'09_LOGS/test_report.json'
                self.send_json(200,{"app":"NaverBlogWorkspace","version":"1.0.0","token":self.server.token,
                  "image":cfg['image'],"network_price_collection":False,"auto_publish":False,
                  "latest_run":json.loads(latest.read_text(encoding='utf-8')) if latest.exists() else None,
                  "qa":json.loads(qa.read_text(encoding='utf-8')) if qa.exists() else None})
                return
            if path in ('/','/index.html'):
                self.send_blob(200,(root/'06_UI/index.html').read_bytes(),'text/html; charset=utf-8');return
            if path.startswith('/output/'):
                base=(root/'08_OUTPUT/runs').resolve()
                file=(base/path[len('/output/'):]).resolve()
                if not file.is_relative_to(base) or not file.is_file() or file.suffix.lower() not in {'.html','.jpg','.png','.json','.md'}:
                    self.send_json(404,{"error":"NOT_FOUND"});return
                self.send_blob(200,file.read_bytes(),(mimetypes.guess_type(file.name)[0] or 'text/plain')+('; charset=utf-8' if file.suffix in {'.html','.json','.md'} else ''));return
            self.send_json(404,{"error":"NOT_FOUND"})
        except (ValueError,OSError,KeyError) as e:
            self.send_json(400,{"error":str(e)[:300]})
    def do_POST(self):
        if not self.trusted(mutation=True):
            self.send_json(403,{"error":"LOCAL_ORIGIN_AND_TOKEN_REQUIRED"});return
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self.send_json(415,{"error":"JSON_REQUIRED"});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=12*1024*1024:
                self.send_json(413,{"error":"BODY_TOO_LARGE_OR_EMPTY"});return
            payload=json.loads(self.rfile.read(size).decode('utf-8'))
            if not isinstance(payload,dict):raise ValueError('JSON_OBJECT_REQUIRED')
        except (ValueError,UnicodeError) as e:
            self.send_json(400,{"error":str(e)[:200]});return
        if not self.server.mutation_lock.acquire(blocking=False):
            self.send_json(409,{"error":"다른 작업이 진행 중입니다. 완료 후 다시 실행하세요."});return
        try:
            root=self.server.root
            path=urlsplit(self.path).path
            if path=='/api/run':
                mode=payload.get('mode','MANUAL_IMPORT')
                records=payload.get('records')
                result=run_pipeline(root,records,mode)
                if payload.get('persist_input') is True and mode=='MANUAL_IMPORT':
                    atomic_json(root/'07_DATA/inbox/products.json',{"records":records})
                self.send_json(200,result)
            elif path=='/api/image':
                encoded=payload.get('data','')
                if not isinstance(encoded,str):raise ValueError('BASE64_REQUIRED')
                data=base64.b64decode(encoded,validate=True)
                relative=store_original(root,data,payload.get('rights','unknown'),
                                        str(payload.get('source','local_upload'))[:2048],str(payload.get('credit',''))[:500])
                self.send_json(200,{"image_path":relative})
            elif path=='/api/image-config':
                self.send_json(200,save_image_config(root,payload))
            elif path=='/api/brief':
                text=payload.get('text','')
                if not isinstance(text,str) or not 1<=len(text)<=50000:raise ValueError('BRIEF_SIZE_INVALID')
                folder=root/'04_CONTENT/briefs';folder.mkdir(exist_ok=True)
                name='brief_'+hashlib.sha256(text.encode()).hexdigest()[:12]+'.md'
                (folder/name).write_text(text,encoding='utf-8')
                self.send_json(200,{"saved":str((folder/name).relative_to(root))})
            else:
                self.send_json(404,{"error":"NOT_FOUND"})
        except (ValueError,OSError,KeyError,binascii.Error) as e:
            self.send_json(400,{"error":str(e)[:300]})
        except Exception as e:
            print('[ERROR]',type(e).__name__)
            self.send_json(500,{"error":"INTERNAL_ERROR: console log를 확인하세요."})
        finally:
            self.server.mutation_lock.release()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int)
    args=parser.parse_args()
    config=load_config(ROOT)
    port=args.port if args.port is not None else config['server']['port']
    try:
        server=LocalServer(('127.0.0.1',port))
    except OSError as e:
        raise SystemExit(f'[ERROR] Port {port} is unavailable. Close the previous workspace server or change settings.local.json. {e}')
    url='http://'+server.authority
    print(f'Workspace: {url}\nLocal only. No price scraping or publication. Keep this window open. Ctrl+C stops it.',flush=True)
    if not args.no_browser:
        threading.Timer(0.7,lambda:webbrowser.open(url,new=1)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
if __name__=='__main__':
    main()
