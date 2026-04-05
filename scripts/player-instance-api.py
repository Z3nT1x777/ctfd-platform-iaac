#!/usr/bin/env python3
from __future__ import annotations

import collections
import hashlib
import hmac
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

MANAGER = "/opt/ctf/orchestrator/player-instance-manager.sh"
API_TOKEN = os.environ.get("ORCHESTRATOR_API_TOKEN", "")
RATE_LIMIT_PER_MIN = int(os.environ.get("ORCHESTRATOR_RATE_LIMIT_PER_MIN", "60"))
API_BIND = os.environ.get("ORCHESTRATOR_API_BIND", "127.0.0.1")
API_PORT = int(os.environ.get("ORCHESTRATOR_API_PORT", "18181"))
SIGNING_SECRET = os.environ.get("ORCHESTRATOR_SIGNING_SECRET", "")
TEAM_RATE_LIMIT_PER_MIN = int(os.environ.get("ORCHESTRATOR_TEAM_RATE_LIMIT_PER_MIN", "30"))
TEAM_MAX_ACTIVE = int(os.environ.get("ORCHESTRATOR_TEAM_MAX_ACTIVE", "3"))
AUDIT_LOG_PATH = os.environ.get("ORCHESTRATOR_AUDIT_LOG", "/var/log/ctf/orchestrator-audit.log")
CTFD_WEBHOOK_TOKEN = os.environ.get("ORCHESTRATOR_CTFD_WEBHOOK_TOKEN", "")
SIGNATURE_TTL_SEC = int(os.environ.get("ORCHESTRATOR_SIGNATURE_TTL_SEC", "300"))
UI_REQUIRE_TOKEN = os.environ.get("ORCHESTRATOR_UI_REQUIRE_TOKEN", "1") == "1"

_rate_lock = threading.Lock()
_rate_state: dict[str, collections.deque[float]] = {}
_team_rate_lock = threading.Lock()
_team_rate_state: dict[str, collections.deque[float]] = {}
_audit_lock = threading.Lock()


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


def is_team_rate_limited(team: str) -> bool:
    if not team or TEAM_RATE_LIMIT_PER_MIN <= 0:
        return False

    now = time.time()
    window_start = now - 60.0

    with _team_rate_lock:
        bucket = _team_rate_state.setdefault(team, collections.deque())
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= TEAM_RATE_LIMIT_PER_MIN:
            return True

        bucket.append(now)
        return False


def run_manager(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(["bash", MANAGER] + args, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def parse_status_lines(stdout: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        row: dict[str, str] = {}
        for pair in line.split(" "):
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            row[key] = value
        if row:
            rows.append(row)
    return rows


def active_instances_for_team(team: str) -> int:
    if not team:
        return 0

    code, out, _err = run_manager(["status"])
    if code != 0:
        return 0

    count = 0
    for row in parse_status_lines(out):
        if row.get("team") == team and row.get("state") == "running":
            count += 1
    return count


def normalize_signature(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if value.startswith("sha256="):
        return value.split("=", 1)[1]
    return value


def ensure_audit_parent() -> None:
    parent = Path(AUDIT_LOG_PATH).parent
    parent.mkdir(parents=True, exist_ok=True)


def write_audit(event: str, **fields: object) -> None:
    record = {
        "ts": int(time.time()),
        "event": event,
        **fields,
    }

    with _audit_lock:
        try:
            ensure_audit_parent()
            with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        except OSError:
            # Keep API responsive even if log file is unavailable.
            pass


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
            <button onclick="extendInstance()">Add 30m</button>
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
        function authHeaders(bodyText) {
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
            const bodyText = payload ? JSON.stringify(payload) : '';
            const res = await fetch(path, {
                method,
                headers: authHeaders(bodyText),
                body: payload ? bodyText : undefined
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

        async function extendInstance() {
            const challenge = challengeInput();
            const team = teamInput();
            if (!challenge || !team) {
                writeResponse({ ok: false, error: 'challenge and team are required' });
                return;
            }
            await callApi('/extend', 'POST', { challenge, team, ttl_min: 30 });
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


class Handler(BaseHTTPRequestHandler):
    def _html_response(self, status: int, body_text: str) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_raw_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length) if length else b""

    def _parse_json_body(self, raw: bytes) -> dict:
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

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

    def _ctfd_token_valid(self) -> bool:
        if not CTFD_WEBHOOK_TOKEN:
            return True
        return self.headers.get("X-CTFd-Webhook-Token", "") == CTFD_WEBHOOK_TOKEN

    def _signature_valid(self, raw_body: bytes) -> tuple[bool, str]:
        if not SIGNING_SECRET:
            return True, "signature_not_enforced"

        ts_header = self.headers.get("X-Signature-Timestamp", "").strip()
        sig_header = normalize_signature(self.headers.get("X-Signature", ""))

        if not ts_header or not sig_header:
            return False, "missing_signature_headers"

        try:
            ts = int(ts_header)
        except ValueError:
            return False, "invalid_signature_timestamp"

        now = int(time.time())
        if abs(now - ts) > SIGNATURE_TTL_SEC:
            return False, "signature_timestamp_expired"

        message = f"{ts_header}.".encode("utf-8") + raw_body
        expected = hmac.new(SIGNING_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig_header, expected):
            return False, "signature_mismatch"

        return True, "ok"

    def _team_from_payload(self, data: dict) -> str:
        team = str(data.get("team", "")).strip().lower()
        return team

    def _audit_http(self, event: str, status: int, path: str, team: str = "", challenge: str = "", detail: str = "") -> None:
        write_audit(
            event,
            http_status=status,
            path=path,
            client=self._get_client_id(),
            team=team,
            challenge=challenge,
            detail=detail,
        )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ["/", "/ui"]:
            if UI_REQUIRE_TOKEN and API_TOKEN:
                query = parse_qs(parsed.query)
                query_token = ""
                if "token" in query and query["token"]:
                    query_token = str(query["token"][0]).strip()

                header_token = self.headers.get("X-Orchestrator-Token", "").strip()
                if header_token != API_TOKEN and query_token != API_TOKEN:
                    self._audit_http("unauthorized_ui", 401, path, detail="missing_or_invalid_ui_token")
                    self._json_response(401, {"ok": False, "error": "unauthorized"})
                    return

            self._html_response(200, UI_HTML)
            return

        if path == "/health":
            self._json_response(200, {"status": "ok"})
            return

        if not self._is_authorized():
            self._audit_http("unauthorized", 401, path, detail="missing_or_invalid_token")
            self._json_response(401, {"ok": False, "error": "unauthorized"})
            return

        if is_rate_limited(self._get_client_id()):
            self._audit_http("rate_limited_client", 429, path)
            self._json_response(429, {"ok": False, "error": "rate_limit_exceeded"})
            return

        if path == "/status":
            code, out, err = run_manager(["status"])
            payload = {"ok": code == 0, "stdout": out, "stderr": err}
            http_status = 200 if code == 0 else 500
            self._audit_http("status", http_status, path)
            self._json_response(http_status, payload)
            return

        self._json_response(404, {"error": "not found"})

    def _execute_action(self, path: str, data: dict) -> tuple[int, dict]:
        team = self._team_from_payload(data)
        challenge = str(data.get("challenge", "")).strip()

        if team and is_team_rate_limited(team):
            payload = {"ok": False, "error": "team_rate_limit_exceeded"}
            return 429, payload

        if path == "/start":
            if TEAM_MAX_ACTIVE > 0 and team:
                active = active_instances_for_team(team)
                if active >= TEAM_MAX_ACTIVE:
                    payload = {
                        "ok": False,
                        "error": "team_quota_exceeded",
                        "team": team,
                        "active_instances": active,
                        "max_active": TEAM_MAX_ACTIVE,
                    }
                    return 409, payload

            args = [
                "start",
                "--challenge",
                challenge,
                "--team",
                team,
                "--ttl-min",
                str(data.get("ttl_min", 60)),
            ]
            if data.get("port") is not None:
                args.extend(["--port", str(data["port"])])

        elif path == "/stop":
            args = [
                "stop",
                "--challenge",
                challenge,
                "--team",
                team,
            ]

        elif path == "/extend":
            ttl_min_raw = data.get("ttl_min", 30)
            ttl_min = int(ttl_min_raw) if str(ttl_min_raw).isdigit() else 30
            args = [
                "extend",
                "--challenge",
                challenge,
                "--team",
                team,
                "--ttl-min",
                str(ttl_min),
            ]

        elif path == "/cleanup":
            args = ["cleanup"]

        else:
            return 404, {"ok": False, "error": "not_found"}

        code, out, err = run_manager(args)
        payload = {"ok": code == 0, "stdout": out, "stderr": err}
        return (200 if code == 0 else 400), payload

    def _handle_ctfd_event(self, data: dict) -> tuple[int, dict]:
        event = str(data.get("event", "")).strip().lower()
        team = str(data.get("team") or data.get("team_id") or "").strip().lower()
        challenge = str(data.get("challenge") or data.get("challenge_name") or "").strip()
        ttl_min = int(data.get("ttl_min", 60)) if str(data.get("ttl_min", "60")).isdigit() else 60

        if event in {"challenge.start", "instance.start", "start"}:
            status, payload = self._execute_action(
                "/start",
                {
                    "team": team,
                    "challenge": challenge,
                    "ttl_min": ttl_min,
                    "port": data.get("port"),
                },
            )
            payload["mapped_event"] = "start"
            return status, payload

        if event in {"challenge.stop", "instance.stop", "stop"}:
            status, payload = self._execute_action(
                "/stop",
                {
                    "team": team,
                    "challenge": challenge,
                },
            )
            payload["mapped_event"] = "stop"
            return status, payload

        if event in {"cleanup", "instance.cleanup"}:
            status, payload = self._execute_action("/cleanup", {})
            payload["mapped_event"] = "cleanup"
            return status, payload

        return 400, {"ok": False, "error": "unsupported_ctfd_event", "event": event}

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        raw_body = self._read_raw_body()
        data = self._parse_json_body(raw_body)
        team = self._team_from_payload(data)
        challenge = str(data.get("challenge", "")).strip()

        if not self._is_authorized():
            self._audit_http("unauthorized", 401, path, team=team, challenge=challenge, detail="missing_or_invalid_token")
            self._json_response(401, {"ok": False, "error": "unauthorized"})
            return

        signature_ok, signature_reason = self._signature_valid(raw_body)
        if not signature_ok:
            self._audit_http("signature_rejected", 401, path, team=team, challenge=challenge, detail=signature_reason)
            self._json_response(401, {"ok": False, "error": signature_reason})
            return

        if is_rate_limited(self._get_client_id()):
            self._audit_http("rate_limited_client", 429, path, team=team, challenge=challenge)
            self._json_response(429, {"ok": False, "error": "rate_limit_exceeded"})
            return

        if path == "/ctfd/event":
            if not self._ctfd_token_valid():
                self._audit_http("ctfd_token_rejected", 401, path, team=team, challenge=challenge)
                self._json_response(401, {"ok": False, "error": "invalid_ctfd_webhook_token"})
                return
            status, payload = self._handle_ctfd_event(data)
            self._audit_http("ctfd_event", status, path, team=team, challenge=challenge, detail=str(payload.get("mapped_event", "")))
            self._json_response(status, payload)
            return

        status, payload = self._execute_action(path, data)
        self._audit_http(path.lstrip("/") or "post", status, path, team=team, challenge=challenge)
        self._json_response(status, payload)


def main() -> None:
    server = HTTPServer((API_BIND, API_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
