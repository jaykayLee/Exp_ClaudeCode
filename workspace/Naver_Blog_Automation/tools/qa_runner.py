from __future__ import annotations
import json
import platform
import sys
import unittest
from environment import ROOT
from nbcore.validation import now_kst

ADDON = ROOT / '11_ADDONS/DANAWA_SNAPSHOT_PROBE'


def main():
    # Workspace tests (10_TESTS) and, since P05, the bundled snapshot add-on tests.
    suite = unittest.defaultTestLoader.discover(str(ROOT / '10_TESTS'), pattern='test_*.py')
    suites = {'workspace': suite.countTestCases()}
    if (ADDON / 'tests').is_dir():
        sys.path.insert(0, str(ADDON))
        addon = unittest.TestLoader().discover(str(ADDON / 'tests'), pattern='test_*.py', top_level_dir=str(ADDON / 'tests'))
        suites['snapshot_addon'] = addon.countTestCases()
        suite.addTests(addon)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {'checked_at': now_kst().isoformat(), 'runtime': platform.platform(), 'python': platform.python_version(),
               'tests': result.testsRun, 'suites': suites, 'failures': len(result.failures), 'errors': len(result.errors),
               'skipped': len(result.skipped), 'passed': result.wasSuccessful(), 'live_source_tested': False,
               'naver_posting_tested': False, 'windows_installation_tested': sys.platform == 'win32',
               'scope': 'Offline code and local HTTP tests; BAT installation needs Windows verification'}
    (ROOT / '09_LOGS').mkdir(exist_ok=True)
    (ROOT / '09_LOGS/test_report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
