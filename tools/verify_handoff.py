"""Verify the pristine handoff package. No downloads, installation or live calls.

After development, hashes are expected to differ; create a new release manifest.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile, BadZipFile

ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    try:
        manifest = json.loads((ROOT / 'ARTIFACT_MANIFEST.json').read_text(encoding='utf-8'))
        failures = []
        for item in manifest['files']:
            p = ROOT / item['path']
            if not p.is_file():
                failures.append('MISSING: ' + item['path'])
                continue
            if hashlib.sha256(p.read_bytes()).hexdigest() != item['sha256']:
                failures.append('HASH_MISMATCH: ' + item['path'])
        for p in (ROOT / 'reference' / 'originals').glob('*.zip'):
            with ZipFile(p) as z:
                bad = z.testzip()
                if bad:
                    failures.append('ZIP_CRC: ' + p.name + ': ' + bad)
        inventory = json.loads((ROOT / 'SOURCE_INVENTORY.json').read_text(encoding='utf-8'))
        missing = [x['file'] for x in inventory['sources'] if x['status'] == 'NOT_RETRIEVED']
        print('Historical inputs NOT INCLUDED (not a download error):')
        for name in missing:
            print('  ' + name)
        print('Baseline originals complete:', inventory['historical_baseline_complete'])
        if failures:
            print('\n'.join(failures))
            return 1
        print('PASS: pristine handoff hashes and included original ZIP CRCs.')
        print('NOT a claim of Windows, live scraping, E2E or blog publication success.')
        return 0
    except (OSError, ValueError, KeyError, BadZipFile) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
