#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

MANAGER = "/opt/ctf/orchestrator/player-instance-manager.sh"


def run_manager(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(["bash", MANAGER] + args, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


class Handler(BaseHTTPRequestHandler):
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
        if path == "/health":
            self._json_response(200, {"status": "ok"})
            return
        if path == "/status":
            code, out, err = run_manager(["status"])
            payload = {"ok": code == 0, "stdout": out, "stderr": err}
            self._json_response(200 if code == 0 else 500, payload)
            return
        self._json_response(404, {"error": "not found"})

    def do_POST(self) -> None:
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
    server = HTTPServer(("0.0.0.0", 8181), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
