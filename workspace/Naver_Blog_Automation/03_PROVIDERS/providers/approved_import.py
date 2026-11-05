from pathlib import Path
import json
from nbcore.validation import normalize_records

def load_approved_input(path: Path) -> list[dict]:
    if path.stat().st_size>2*1024*1024:
        raise ValueError("입력 JSON은 2 MiB 이하여야 합니다.")
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    records=data.get("records") if isinstance(data,dict) else data
    return normalize_records(records)
