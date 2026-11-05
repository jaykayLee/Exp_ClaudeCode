from __future__ import annotations
import argparse
import json
import sys
from environment import ROOT
from nbcore.pipeline import run_pipeline

def main() -> int:
    parser=argparse.ArgumentParser(description="Local review only; never posts to a blog.")
    parser.add_argument("--demo",action="store_true")
    args=parser.parse_args()
    input_path=ROOT/("07_DATA/samples/products_demo.json" if args.demo else "07_DATA/inbox/products.json")
    try:
        if input_path.stat().st_size>2*1024*1024:
            raise ValueError("INPUT_TOO_LARGE: max 2 MiB")
        payload=json.loads(input_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload,dict):
            raise ValueError("INPUT_OBJECT_REQUIRED: use {records: [...]} JSON")
        report=run_pipeline(ROOT,payload.get("records",[]),"DEMO" if args.demo else "MANUAL_IMPORT")
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError) as e:
        print("[ERROR] "+str(e),file=sys.stderr)
        return 1
if __name__=="__main__":
    raise SystemExit(main())
