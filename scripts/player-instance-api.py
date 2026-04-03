#!/usr/bin/env python3
from __future__ import annotations

import collections
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

MANAGER = "/opt/ctf/orchestrator/player-instance-manager.sh"
API_TOKEN = os.environ.get("ORCHESTRATOR_API_TOKEN", "")
RATE_LIMIT_PER_MIN = int(os.environ.get("ORCHESTRATOR_RATE_LIMIT_PER_MIN", "60"))
API_BIND = os.environ.get("ORCHESTRATOR_API_BIND", "0.0.0.0")
API_PORT = int(os.environ.get("ORCHESTRATOR_API_PORT", "8181"))

_rate_lock = threading.Lock()
_rate_state: dict[str, collections.deque[float]] = {}


def is_rate_limited(client_id: str) -> bool:
    now = time.time()
    window_start = now - 60.0

    with _rate_lock:
        bucket = _rate_state.setdefault(client_id, collections.deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT_PER_MIN:
            return True

        bucket.append(now)
        return False

UI_HTML = """<!doctype html>
<html>
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <title>CTF Instance Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 24px; max-width: 900px; }
        h1 { margin-bottom: 12px; }
        .row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
        input { padding: 8px; }
        button { padding: 8px 12px; cursor: pointer; }
        pre { background: #111; color: #eee; padding: 12px; overflow: auto; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-top: 12px; }
    </style>
</head>
<body>
    <h1>CTF Player Instance Control</h1>
    <p>Start/stop per-team challenge instances with TTL.</p>

    <div class=\"card\">
        <div class=\"row\">
            <input id=\"challenge\" placeholder=\"challenge (ex: web-01-test)\" />
            <input id=\"team\" placeholder=\"team (ex: team-alpha)\" />
            <input id=\"ttl\" type=\"number\" min=\"1\" max=\"240\" value=\"60\" />
            <input id=\"token\" placeholder=\"optional bearer token\" style=\"min-width:260px\" />
        </div>
        <div class=\"row\">
            <button onclick=\"startInstance()\">Start 1h</button>
            <button onclick=\"stopInstance()\">Stop</button>
            <button onclick=\"refreshStatus()\">Refresh Status</button>
        </div>
    </div>

    <div class=\"card\">
        <h3>Active Instances</h3>
        <pre id=\"status\">No data yet</pre>
    </div>

    <div class=\"card\">
        <h3>Last API Response</h3>
        <pre id=\"response\">No action yet</pre>
    </div>

    <script>
        function authHeaders() {
            const token = document.getElementById('token').value.trim();
            const h = { 'Content-Type': 'application/json' };
            if (token) h['Authorization'] = `Bearer ${token}`;
            return h;
        }

        function challengeInput() {
            return document.getElementById('challenge').value.trim();
        }

        function teamInput() {
            return document.getElementById('team').value.trim();
        }

        function ttlInput() {
            return Number(document.getElementById('ttl').value || 60);
        }

        function writeResponse(data) {
            document.getElementById('response').textContent = JSON.stringify(data, null, 2);
        }

        function parseStatusLines(stdout) {
            const now = Math.floor(Date.now() / 1000);
            return (stdout || '').split('\n').filter(Boolean).map(line => {
                const obj = {};
                line.split(' ').forEach(kv => {
                    const [k, v] = kv.split('=');
                    if (k) obj[k] = v;
                });
                const remaining = Number(obj.ttl_remaining_sec || 0);
                obj.ttl_remaining_human = remaining > 0 ? `${Math.floor(remaining / 60)}m ${remaining % 60}s` : 'expired';
                obj.checked_at_epoch = now;
                return obj;
            });
        }

        async function callApi(path, method, payload) {
            const res = await fetch(path, {
                method,
                headers: authHeaders(),
                body: payload ? JSON.stringify(payload) : undefined
            });
            const data = await res.json();
            writeResponse(data);
            if (path !== '/status') await refreshStatus();
            return data;
        }

        async function startInstance() {
            const challenge = challengeInput();
            const team = teamInput();
            const ttl_min = ttlInput();
            if (!challenge || !team) {
                writeResponse({ ok: false, error: 'challenge and team are required' });
                return;
            }
            await callApi('/start', 'POST', { challenge, team, ttl_min });
        }

        async function stopInstance() {
            const challenge = challengeInput();
            const team = teamInput();
            if (!challenge || !team) {
                writeResponse({ ok: false, error: 'challenge and team are required' });
                return;
            }
            await callApi('/stop', 'POST', { challenge, team });
        }

        async function refreshStatus() {
            const data = await callApi('/status', 'GET');
            const parsed = parseStatusLines(data.stdout || '');
            document.getElementById('status').textContent = JSON.stringify(parsed, null, 2);
        }

        setInterval(refreshStatus, 10000);
        refreshStatus();
    </script>
</body>
</html>
"""


def run_manager(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(["bash", MANAGER] + args, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


class Handler(BaseHTTPRequestHandler):
    def _html_response(self, status: int, body_text: str) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_client_id(self) -> str:
        return self.headers.get("X-Forwarded-For") or self.client_address[0]

    def _is_authorized(self) -> bool:
        if not API_TOKEN:
            return True

        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header.split(" ", 1)[1].strip()
            return token == API_TOKEN

        token = self.headers.get("X-Orchestrator-Token", "")
        return token == API_TOKEN

    def _json_response(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ["/", "/ui"]:
            self._html_response(200, UI_HTML)
            return
        if path == "/health":
            self._json_response(200, {"status": "ok"})
            return

        if not self._is_authorized():
            self._json_response(401, {"ok": False, "error": "unauthorized"})
            return

        if is_rate_limited(self._get_client_id()):
            self._json_response(429, {"ok": False, "error": "rate_limit_exceeded"})
            return

        if path == "/status":
            code, out, err = run_manager(["status"])
            payload = {"ok": code == 0, "stdout": out, "stderr": err}
            self._json_response(200 if code == 0 else 500, payload)
            return
        self._json_response(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._is_authorized():
            self._json_response(401, {"ok": False, "error": "unauthorized"})
            return

        if is_rate_limited(self._get_client_id()):
            self._json_response(429, {"ok": False, "error": "rate_limit_exceeded"})
            return

        path = urlparse(self.path).path
        data = self._read_json()

        if path == "/start":
            args = [
                "start",
                "--challenge",
                str(data.get("challenge", "")),
                "--team",
                str(data.get("team", "")),
                "--ttl-min",
                str(data.get("ttl_min", 60)),
            ]
            if data.get("port") is not None:
                args.extend(["--port", str(data["port"])])
        elif path == "/stop":
            args = [
                "stop",
                "--challenge",
                str(data.get("challenge", "")),
                "--team",
                str(data.get("team", "")),
            ]
        elif path == "/cleanup":
            args = ["cleanup"]
        else:
            self._json_response(404, {"error": "not found"})
            return

        code, out, err = run_manager(args)
        payload = {"ok": code == 0, "stdout": out, "stderr": err}
        self._json_response(200 if code == 0 else 400, payload)


def main() -> None:
    server = HTTPServer((API_BIND, API_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
