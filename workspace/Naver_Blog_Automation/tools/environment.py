from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
for name in ("02_CORE", "03_PROVIDERS", "05_PUBLISHERS"):
    sys.path.insert(0, str(ROOT / name))
