from __future__ import annotations
import json
import platform
import struct
import sys
from environment import ROOT
from nbcore.config import load_config
from nbcore.validation import now_kst

def inspect():
    checks=[]
    def add(name,status,detail):checks.append({'name':name,'status':status,'detail':detail})
    add('Python','PASS' if (3,11)<=sys.version_info[:2]<(3,14) else 'FAIL',platform.python_version())
    add('64bit','PASS' if struct.calcsize('P')==8 else 'FAIL',str(struct.calcsize('P')*8))
    try:
        from PIL import Image, __version__
        add('Pillow','PASS' if __version__=='12.3.0' else 'WARN',__version__+' (lock:12.3.0)')
    except ImportError:
        add('Pillow','FAIL','Run install.bat')
    try:
        cfg=load_config(ROOT)
        add('Config','PASS','Local-only / auto_publish=false')
        test=ROOT/'09_LOGS/.write_test';test.write_text('OK');test.unlink()
        add('Writable workspace','PASS',str(ROOT))
    except (OSError,ValueError,KeyError) as e:
        add('Config / write access','FAIL',str(e))
    try:
        from run_once import lock_info
        lock=lock_info(ROOT)
        add('Pipeline lock','PASS' if lock is None else 'WARN',
            'No lock' if lock is None else f"Lock exists: {lock}. Delete 07_DATA/state/pipeline.lock only after confirming no run is active.")
    except (ImportError,OSError,ValueError) as e:
        add('Pipeline lock','WARN',str(e))
    addon=ROOT/'11_ADDONS/DANAWA_SNAPSHOT_PROBE/probe/snapshot_probe.py'
    add('Snapshot add-on','PASS' if addon.is_file() else 'WARN','Saved-HTML bridge (offline, no network)' if addon.is_file() else 'Missing; snapshot bridge unavailable')
    add('Danawa live collector','NOT_CONFIGURED','Approved import only; live permission and selector validation required')
    add('Naver shopping legacy API','RETIRED','Official retirement: 2026-07-31. No API key setup needed for this baseline.')
    add('Naver publication','DISABLED','Manual handoff only')
    add('Windows BAT runtime','USER_PC_REQUIRED' if sys.platform!='win32' else 'CURRENT_PC','No claim of verification on another PC')
    result={'checked_at':now_kst().isoformat(),'platform':platform.platform(),'checks':checks,'local_ok':not any(x['status']=='FAIL' for x in checks)}
    (ROOT/'09_LOGS').mkdir(exist_ok=True)
    (ROOT/'09_LOGS/doctor_report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result
if __name__=='__main__':
    result=inspect();print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['local_ok'] else 1)
