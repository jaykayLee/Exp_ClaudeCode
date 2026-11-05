from __future__ import annotations
from pathlib import Path
import json
import shutil

RUNTIME_DIRS = ("07_DATA/inbox", "07_DATA/images/original", "07_DATA/images/resized",
                "07_DATA/state", "08_OUTPUT/runs", "09_LOGS")

def initialize(root: Path) -> None:
    for folder in RUNTIME_DIRS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    target = root / "01_CONFIG/settings.local.json"
    if not target.exists():
        shutil.copyfile(root / "01_CONFIG/settings.example.json", target)

def load_config(root: Path) -> dict:
    initialize(root)
    config = json.loads((root / "01_CONFIG/settings.local.json").read_text(encoding="utf-8-sig"))
    return validate_config(config)

def validate_config(config: dict) -> dict:
    if not isinstance(config, dict) or config.get("auto_publish") is not False:
        raise ValueError("자동 발행은 이 버전에서 사용할 수 없습니다.")
    image = config["image"]
    for key in ("width_px", "height_px"):
        if type(image.get(key)) is not int or not 80 <= image[key] <= 2000:
            raise ValueError("이미지 가로/세로는 80~2000 사이 정수여야 합니다.")
    if type(image.get("dpi")) is not int or not 72 <= image["dpi"] <= 600:
        raise ValueError("DPI는 72~600 사이 정수여야 합니다.")
    if image.get("background") != "white":
        raise ValueError("v1.0에서는 흰색 배경을 사용합니다.")
    if type(image.get("download_enabled")) is not bool:
        raise ValueError("download_enabled는 true/false 값이어야 합니다.")
    if not isinstance(image.get("allowed_hosts"), list) or any(not isinstance(h,str) or not h or len(h)>253 or "/" in h or "*" in h for h in image["allowed_hosts"]):
        raise ValueError("허용 호스트는 와일드카드 없는 정확한 도메인 목록이어야 합니다.")
    for key, cap in (("max_bytes", 8388608), ("max_pixels", 20000000)):
        if type(image.get(key)) is not int or not 1 <= image[key] <= cap:
            raise ValueError(f"{key}가 허용 범위를 벗어났습니다.")
    age = config.get("quality",{}).get("max_price_age_hours")
    if type(age) is not int or not 1 <= age <= 168:
        raise ValueError("가격 유효기간은 1~168시간 정수여야 합니다.")
    if config.get("server",{}).get("host") != "127.0.0.1":
        raise ValueError("서버는 127.0.0.1에만 바인딩할 수 있습니다.")
    port=config["server"].get("port")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("포트는 1024~65535 사이여야 합니다.")
    return config

def save_image_config(root: Path, updates: dict) -> dict:
    config = load_config(root)
    allowed = {"width_px", "height_px", "dpi", "download_enabled", "allowed_hosts"}
    if not isinstance(updates, dict) or set(updates) - allowed:
        raise ValueError("이미지 설정에서 허용되지 않은 항목입니다.")
    config["image"].update(updates)
    validate_config(config)
    path=root / "01_CONFIG/settings.local.json"
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    return config["image"]
