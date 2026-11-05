"""Start the real local panel server (what start_panel.bat runs, minus the browser) and check it over HTTP.

Checks: status API, Host guard, token guard, snapshot demo via API, generated table + paste table served.
Synthetic data only, writes into a temporary copy of the workspace. Exit 0 = all checks passed.
  .venv/bin/python 00_PROJECT/QA/server_smoke.py      (Windows: .venv\\Scripts\\python.exe ...)
"""
from __future__ import annotations

import http.client
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
checks: list[tuple[str, bool, str]] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    checks.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (" — " + detail if detail else ""), flush=True)


def call(port: int, method: str, path: str, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    h = {"Host": f"127.0.0.1:{port}"}
    h.update(headers or {})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if data is not None:
        h["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=h)
    r = conn.getresponse()
    payload = r.read()
    conn.close()
    return r.status, payload


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="server_smoke_") as temp:
        root = Path(temp) / "패널 점검 Naver_Blog_Automation"
        shutil.copytree(APP, root, ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "08_OUTPUT", "09_LOGS"))
        settings = root / "01_CONFIG/settings.local.json"
        cfg = json.loads((root / "01_CONFIG/settings.example.json").read_text(encoding="utf-8"))
        with socket_port() as port:
            cfg["server"]["port"] = port
        settings.write_text(json.dumps(cfg), encoding="utf-8")
        proc = subprocess.Popen([sys.executable, str(root / "tools/server.py"), "--no-browser"],
                                cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env={**__import__("os").environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        try:
            status = None
            for _ in range(60):
                try:
                    status = call(port, "GET", "/api/status")
                    break
                except OSError:
                    time.sleep(0.5)
            ok("server_started_on_127.0.0.1", status is not None and status[0] == 200, f"port {port}")
            if status is None:
                return 1
            info = json.loads(status[1])
            ok("status_local_only", info["auto_publish"] is False and info["network_price_collection"] is False)
            token = info["token"]
            ok("host_guard", call(port, "GET", "/api/status", headers={"Host": "evil.example"})[0] == 403)
            ok("token_guard", call(port, "POST", "/api/snapshot", {"demo": True})[0] == 403)
            code, data = call(port, "POST", "/api/snapshot", {"demo": True}, {"X-Workspace-Token": token})
            ok("snapshot_demo_api", code == 200, data[:200].decode("utf-8", "replace") if code != 200 else "")
            if code == 200:
                result = json.loads(data)
                rows = result["status_rows"]
                ok("status_rows", [r["danawa_status"] for r in rows] == ["SELECTED", "NO_ELIGIBLE_CANDIDATE", "NO_CANDIDATE"])
                ok("korean_text_intact", "총액 119,000원" in rows[0]["detail"] and rows[1]["query"] == "가상 키보드 B")
                ok("gate_demo_only", result["review_gate"] == "DEMO_ONLY")
                code_t, page = call(port, "GET", result["pipeline"]["preview_url"])
                ok("seven_column_table_served", code_t == 200 and page.decode("utf-8").count("<th>") == 7)
                code_p, paste = call(port, "GET", result["paste_url"])
                ok("paste_table_served", code_p == 200 and "<img" not in paste.decode("utf-8"))
        finally:
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
        ok("server_banner_local_only", b"Local only" in out, out.decode("utf-8", "replace").splitlines()[0][:120] if out else "")
    passed = sum(c[1] for c in checks)
    print(json.dumps({"passed": passed, "total": len(checks), "platform": sys.platform}))
    return 0 if passed == len(checks) else 1


class socket_port:
    """Reserve a free localhost port number (released before the server binds)."""
    def __enter__(self) -> int:
        import socket
        self.s = socket.socket()
        self.s.bind(("127.0.0.1", 0))
        return self.s.getsockname()[1]

    def __exit__(self, *exc) -> None:
        self.s.close()


if __name__ == "__main__":
    raise SystemExit(main())
