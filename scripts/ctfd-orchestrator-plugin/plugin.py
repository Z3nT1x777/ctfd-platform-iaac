"""
CTFd Orchestrator Integration Plugin

Handles challenge instance lifecycle:
- Intercepts challenge start/stop events from CTFd UI
- Creates isolated Docker instances via orchestrator API
- Manages per-team quotas and TTL tracking
- Provides UI updates with instance URLs and remaining time
"""

import logging
import html
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from flask import Blueprint, request, jsonify, render_template_string, redirect
from CTFd.models import Challenges, Teams, db
from CTFd.utils.decorators import authed_only, require_team
from CTFd.utils.user import get_current_user

from .webhook_handler import OrchestratorWebhookHandler
from .instance_tracker import InstanceTracker
from .access_profiles import build_access_methods, load_access_hint_from_dir, normalize_slug

logger = logging.getLogger("ctfd.orchestrator_plugin")

UI_TEMPLATE = """
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Team Instances Dashboard</title>
    <style>{% raw %}
        :root {
            --ink: #e6edf7;
            --muted: #9aa8bc;
            --line: #2a3548;
            --panel: rgba(15, 23, 35, 0.9);
            --panel-strong: #111a29;
            --ok-fg: #54d299;
            --ok-bg: rgba(34, 197, 94, 0.16);
            --down-fg: #ff8b8b;
            --down-bg: rgba(239, 68, 68, 0.16);
            --open: #129c52;
            --extend: #2368e8;
            --kill: #dc2626;
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            color: var(--ink);
            font-family: "Plus Jakarta Sans", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            background:
                radial-gradient(900px 560px at 8% -16%, rgba(59, 130, 246, 0.2), transparent 60%),
                radial-gradient(900px 560px at 100% -18%, rgba(16, 185, 129, 0.12), transparent 62%),
                linear-gradient(160deg, #060b14, #0a1320 55%, #0d1524);
        }

        .wrap {
            width: min(1220px, calc(100vw - 34px));
            margin: 0 auto;
            padding: 28px 0 40px;
        }

        .hero {
            display: grid;
            grid-template-columns: 1fr auto;
            gap: 18px;
            margin-bottom: 20px;
            padding: 20px 22px;
            border-radius: 20px;
            border: 1px solid var(--line);
            background: var(--panel);
            backdrop-filter: blur(10px);
            box-shadow: 0 14px 36px rgba(2, 6, 23, 0.42);
        }

        .hero h1 {
            margin: 0 0 6px;
            font-size: 2rem;
            letter-spacing: -0.02em;
            line-height: 1.15;
        }

        .sub {
            margin: 0;
            max-width: 70ch;
            color: var(--muted);
            line-height: 1.5;
        }

        .flash {
            display: none;
            margin-top: 13px;
            padding: 11px 13px;
            border-radius: 12px;
            border: 1px solid var(--line);
            background: var(--panel-strong);
            font-weight: 600;
        }

        .flash.ok,
        .flash.err {
            display: block;
        }

        .flash.ok {
            border-color: rgba(34, 197, 94, 0.36);
            background: rgba(34, 197, 94, 0.14);
            color: #86efac;
        }

        .flash.err {
            border-color: rgba(239, 68, 68, 0.36);
            background: rgba(239, 68, 68, 0.14);
            color: #fca5a5;
        }

        .top-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: flex-start;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            border-radius: 12px;
            padding: 10px 15px;
            border: 1px solid transparent;
            font-weight: 700;
            transition: transform 0.14s ease, box-shadow 0.14s ease;
        }

        .btn:hover {
            transform: translateY(-1px);
        }

        .btn.refresh {
            background: #2368e8;
            border-color: #2368e8;
            color: #fff;
        }

        .btn:not(.refresh) {
            background: var(--panel-strong);
            border-color: var(--line);
            color: var(--ink);
        }

        .grid {
            display: grid;
            grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
            gap: 18px;
        }

        .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 18px;
            box-shadow: 0 12px 28px rgba(2, 6, 23, 0.36);
        }

        .panel h2 {
            margin: 0 0 14px;
            font-size: 1.48rem;
            letter-spacing: -0.01em;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
        }

        .inst {
            display: flex;
            flex-direction: column;
            gap: 12px;
            min-height: 222px;
            padding: 16px;
            border-radius: 18px;
            border: 1px solid var(--line);
            background: var(--panel-strong);
            box-shadow: 0 6px 20px rgba(2, 6, 23, 0.28);
        }

        .inst-head {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: flex-start;
        }

        .name {
            margin: 0;
            font-size: 1.22rem;
            letter-spacing: -0.01em;
            line-height: 1.2;
            word-break: break-word;
        }

        .state {
            white-space: nowrap;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.95rem;
            font-weight: 700;
            color: var(--ok-fg);
            background: var(--ok-bg);
        }

        .state.down {
            color: var(--down-fg);
            background: var(--down-bg);
        }

        .ttlbox {
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 12px;
            background: #0c1625;
        }

        .k {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.11em;
        }

        .v {
            margin-top: 4px;
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            word-break: break-word;
        }

        .actions {
            margin-top: auto;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }

        .action {
            min-height: 40px;
            border: 0;
            border-radius: 12px;
            padding: 10px 13px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            text-decoration: none;
            font-weight: 700;
            line-height: 1;
            color: #fff;
        }

        .action.open {
            grid-column: 1 / -1;
            background: var(--open);
        }

        .action.extend {
            background: var(--extend);
        }

        .action.kill {
            background: var(--kill);
        }

        .leader {
            width: 100%;
            border-collapse: collapse;
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
            background: #0f1827;
        }

        .leader th,
        .leader td {
            padding: 12px;
            border-bottom: 1px solid var(--line);
            text-align: left;
            vertical-align: top;
        }

        .leader th {
            color: var(--muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .leader tr:last-child td {
            border-bottom: 0;
        }

        .empty-state {
            border: 1px dashed var(--line);
            border-radius: 14px;
            padding: 16px;
            text-align: center;
            color: var(--muted);
            background: #0d1624;
        }

        @media (max-width: 980px) {
            .hero {
                grid-template-columns: 1fr;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            .cards {
                grid-template-columns: 1fr;
            }
        }
    {% endraw %}</style>
</head>
<body>
    <div class=\"wrap\">
        <div class=\"hero\">
            <div>
                <h1>Instance Control Center</h1>
                <p class="sub">Team: {{ team_name|e }}. Fast controls, clear status, and clean operations.</p>

                <div id="actionMessage" class="flash{% if initial_message %} {{ initial_kind }}{% endif %}">{{ initial_message|e }}</div>
            </div>
            <div class=\"top-actions\">
                <a class=\"btn\" href=\"/challenges\">Back to Challenges</a>
                <a class=\"btn refresh\" href=\"javascript:void(0)\" onclick=\"refreshAll()\">Refresh</a>
            </div>
        </div>

        <div class=\"grid\">
            <section class=\"panel\">
                <h2>Team Active Instances</h2>
                <div id=\"instances\" class=\"cards\"></div>
            </section>

            <section class=\"panel\">
                <h2>Live Activity</h2>
                <table class=\"leader\">
                    <thead><tr><th>Team</th><th>Active Instances</th></tr></thead>
                    <tbody id=\"leaderboard\"></tbody>
                </table>
            </section>
        </div>
    </div>

    <script>
        const fmt = (sec) => {
            if (sec <= 0) return 'expired';
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return `${m}m ${s}s`;
        };
        const actionMessage = document.getElementById('actionMessage');

        function showMessage(kind, text) {
            actionMessage.className = `flash ${kind}`;
            actionMessage.textContent = text;
        }

        function csrfHeaders() {
            const nonce = (window.init && window.init.csrfNonce) ? window.init.csrfNonce : '';
            return nonce ? { 'CSRF-Token': nonce, 'X-CSRF-Token': nonce } : {};
        }

        async function callInstanceAction(path, payload) {
            try {
                const res = await fetch(path, {
                    method: 'POST',
                    cache: 'no-store',
                    headers: { 'Content-Type': 'application/json', ...csrfHeaders() },
                    body: JSON.stringify(payload)
                });

                const raw = await res.text();
                let data = {};
                try {
                    data = raw ? JSON.parse(raw) : {};
                } catch (_e) {
                    data = {
                        ok: false,
                        error: `http_${res.status}`,
                        detail: raw ? raw.slice(0, 240) : `HTTP ${res.status}`,
                    };
                }

                if (!res.ok) {
                    data.ok = false;
                    if (!data.error) {
                        data.error = `http_${res.status}`;
                    }
                    if (!data.detail) {
                        data.detail = `HTTP ${res.status}`;
                    }
                }

                return data;
            } catch (err) {
                return {
                    ok: false,
                    error: 'network_error',
                    detail: String((err && err.message) || err || 'network_error'),
                };
            }
        }

        async function stopInstance(ref, name) {
            return callInstanceAction('/plugins/orchestrator/stop', {
                challenge_id: (String(ref || '').match(/^\d+$/) ? Number(ref) : undefined),
                challenge_name: name || String(ref || ''),
            });
        }

        async function extendInstance(ref, name) {
            return callInstanceAction('/plugins/orchestrator/extend', {
                challenge_id: (String(ref || '').match(/^\d+$/) ? Number(ref) : undefined),
                challenge_name: name || String(ref || ''),
                ttl_min: 30,
            });
        }

        async function refreshInstances() {
            const res = await fetch('/plugins/orchestrator/instances', { cache: 'no-store' });
            const data = await res.json();
            const body = document.getElementById('instances');
            body.innerHTML = '';

            if (!(data.instances || []).length) {
                body.innerHTML = '<div class="empty-state">No active instances right now.</div>';
                return;
            }

            (data.instances || []).forEach((inst) => {
                const challengeRef = inst.challenge_ref || inst.challenge_name || String(inst.challenge_id || '');
                const ttlSeconds = Number(inst.ttl_remaining_sec || 0);

                const card = document.createElement('div');
                card.className = 'inst';
                card.innerHTML = `
                    <div class=\"inst-head\">
                        <h3 class=\"name\">${inst.challenge_name || '-'}</h3>
                        <span class=\"state ${ttlSeconds > 0 ? '' : 'down'}\">${ttlSeconds > 0 ? 'UP' : 'DOWN'}</span>
                    </div>
                    <div class=\"ttlbox\"><div class=\"k\">TTL Remaining</div><div class=\"v\">${fmt(ttlSeconds)}</div></div>
                    <div class=\"actions\">
                        <a class=\"action open\" href=\"${inst.open_href || '#'}\" ${inst.open_href ? 'target=\"_blank\" rel=\"noopener\"' : ''}>${inst.open_label || 'Open Access'}</a>
                        <a class=\"action extend\" href=\"/plugins/orchestrator/extend-ui?challenge_ref=${encodeURIComponent(challengeRef)}\">Add 30m</a>
                        <a class=\"action kill\" href=\"/plugins/orchestrator/stop-ui?challenge_ref=${encodeURIComponent(challengeRef)}\">Kill Container</a>
                    </div>
                `;

                body.appendChild(card);
            });
        }

        async function refreshLeaderboard() {
            const res = await fetch('/plugins/orchestrator/leaderboard/live', { cache: 'no-store' });
            const data = await res.json();
            const body = document.getElementById('leaderboard');
            body.innerHTML = '';

            if (!(data.rows || []).length) {
                const tr = document.createElement('tr');
                tr.innerHTML = '<td colspan="2" style="color:var(--muted);">No active instances yet.</td>';
                body.appendChild(tr);
                return;
            }

            (data.rows || []).forEach((row) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${row.team_name || row.team_id}</td><td>${row.active_instances}</td>`;
                body.appendChild(tr);
            });
        }

        async function refreshAll() {
            await refreshInstances();
            await refreshLeaderboard();
        }

        refreshAll();
        setInterval(refreshAll, 10000);

        // Smooth countdown between server refreshes so TTL never looks frozen.
        setInterval(() => {
            document.querySelectorAll('#instances .inst .ttlbox .v').forEach((node) => {
                const text = node.textContent || '';
                const match = text.match(/^(\d+)m\s+(\d+)s$/);
                if (!match) return;
                let total = Number(match[1]) * 60 + Number(match[2]);
                if (total <= 0) return;
                total -= 1;
                const m = Math.floor(total / 60);
                const s = total % 60;
                node.textContent = `${m}m ${s}s`;
            });
        }, 1000);
    </script>
</body>
</html>
"""


class OrchestrationPlugin:
    """Main plugin class for CTFd orchestrator integration."""

    def __init__(self, app):
        """Initialize plugin and register routes."""
        self.app = app
        self.orchestrator_handler = OrchestratorWebhookHandler(
            api_url=os.getenv(
                "ORCHESTRATOR_API_URL", "http://host.docker.internal:8181"
            ),
            api_token=os.getenv("ORCHESTRATOR_API_TOKEN", ""),
            signing_secret=os.getenv("ORCHESTRATOR_SIGNING_SECRET", ""),
            webhook_token=os.getenv("ORCHESTRATOR_WEBHOOK_TOKEN", ""),
        )
        self.instance_tracker = InstanceTracker()
        self._challenge_dir_cache: Dict[str, Optional[str]] = {}
        self._register_routes()
        logger.info("CTFd Orchestrator Plugin initialized")

    def _normalize_slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9-]", "", (value or "").strip().lower().replace(" ", "-"))

    def _resolve_challenge_dir_from_name(self, challenge_name: str) -> Optional[str]:
        """Resolve a challenge directory under /vagrant/challenges, including nested layouts."""
        slug = self._normalize_slug(challenge_name)
        if not slug:
            return None

        if slug in self._challenge_dir_cache:
            return self._challenge_dir_cache[slug]

        base = Path("/vagrant/challenges")
        if not base.exists():
            self._challenge_dir_cache[slug] = None
            return None

        # Fast path: direct folder name match.
        direct = base / slug
        if (direct / "challenge.yml").exists():
            resolved = str(direct)
            self._challenge_dir_cache[slug] = resolved
            return resolved

        # Recursive path: match by folder name or challenge.yml name field.
        for yml in base.rglob("challenge.yml"):
            folder = yml.parent
            if self._normalize_slug(folder.name) == slug:
                resolved = str(folder)
                self._challenge_dir_cache[slug] = resolved
                return resolved

            try:
                content = yml.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            m_name = re.search(r"^name:\s*(.+)$", content, flags=re.MULTILINE)
            if m_name and self._normalize_slug(m_name.group(1).strip().strip('"\'')) == slug:
                resolved = str(folder)
                self._challenge_dir_cache[slug] = resolved
                return resolved

        self._challenge_dir_cache[slug] = None
        return None

    def _is_spawnable_challenge_name(self, challenge_name: str) -> bool:
        challenge_dir = self._resolve_challenge_dir_from_name(challenge_name)
        if not challenge_dir:
            return False
        return (Path(challenge_dir) / "docker-compose.yml").exists()

    def _challenge_access_hint(self, challenge) -> Dict[str, str]:
        """Read lightweight access hints from challenge.yml when available."""
        challenge_dir = self._resolve_challenge_dir_from_name(str(getattr(challenge, "name", "") or ""))
        return load_access_hint_from_dir(challenge_dir) if challenge_dir else {
            "mode": "auto",
            "ssh_user": "",
            "ssh_password": "",
            "instructions": "",
            "hint": "",
            "container_port": "",
            "type": "",
        }

    def _build_access_methods(self, challenge, url: str, port: Any, stdout: str) -> List[Dict[str, str]]:
        """Build access methods for front-end rendering without hardcoding challenge categories."""
        challenge_dir = self._resolve_challenge_dir_from_name(str(getattr(challenge, "name", "") or ""))
        if not challenge_dir:
            return []

        return build_access_methods(
            challenge_name=str(getattr(challenge, "name", "") or ""),
            challenge_dir=challenge_dir,
            connection_info=str(getattr(challenge, "connection_info", "") or "").strip(),
            url=str(url or "").strip(),
            port=port,
            stdout=str(stdout or ""),
            player_host=os.getenv("ORCHESTRATOR_PLAYER_HOST", "192.168.56.10"),
            default_ssh_user=os.getenv("ORCHESTRATOR_SSH_USER", "ctf"),
        )

    def _parse_status_rows(self, stdout: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for line in (stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue

            row: Dict[str, str] = {}
            for pair in line.split():
                if "=" not in pair:
                    continue
                key, value = pair.split("=", 1)
                row[key.lower()] = value

            if row:
                rows.append(row)

        return rows

    def _current_status_rows(self) -> List[Dict[str, str]]:
        try:
            result = self.orchestrator_handler.get_status()
        except Exception:
            logger.exception("Failed to query orchestrator status")
            return []

        if not result.get("ok"):
            return []

        return self._parse_status_rows(str(result.get("stdout", "")))

    def _find_status_row(self, team_id: str, challenge_name: str) -> Optional[Dict[str, str]]:
        target = normalize_slug(challenge_name)
        for row in self._current_status_rows():
            if str(row.get("team", "")) != str(team_id):
                continue

            row_target = normalize_slug(str(row.get("challenge") or row.get("project") or ""))
            if row_target == target:
                return row

        return None

    def _build_launch_description(self, challenge, access_methods: List[Dict[str, str]]) -> str:
        methods = {str(m.get("type", "")).strip().lower() for m in access_methods}
        if "web" in methods:
            return "Open the web service below and use the exposed interface for this challenge."
        if "ssh" in methods:
            return "Use one of the SSH commands below to connect to the instance."

        hint = self._challenge_access_hint(challenge)
        instruction = str(hint.get("instructions", "") or "").strip()
        if instruction:
            return instruction

        return "Follow the challenge instructions below to access the instance."

    def _challenge_matches_reference(self, challenge, reference: str) -> bool:
        ref = str(reference or "").strip()
        if not ref:
            return False

        if ref.isdigit() and getattr(challenge, "id", None) is not None:
            return int(ref) == int(challenge.id)

        return normalize_slug(str(getattr(challenge, "name", "") or "")) == normalize_slug(ref)

    def _resolve_challenge_from_reference(self, reference: Any):
        ref = str(reference or "").strip()
        if not ref:
            return None

        if ref.isdigit():
            challenge = Challenges.query.get(int(ref))
            if challenge:
                return challenge

        normalized = normalize_slug(ref)
        if not normalized:
            return None

        for challenge in Challenges.query.all():
            if self._challenge_matches_reference(challenge, ref):
                return challenge

        return None

    def _dashboard_redirect(self, kind: str, message: str):
        return redirect(
            "/plugins/orchestrator/dashboard?kind="
            + quote(str(kind or "ok"))
            + "&msg="
            + quote(str(message or "")),
            code=302,
        )

    def _resolve_current_instance_ttl(self, team_id: str, challenge) -> int:
        current_ttl = 0

        row = self._find_status_row(str(team_id), challenge.name)
        if row and str(row.get("state", "")).strip().lower() == "running":
            current_ttl = max(0, int(row.get("ttl_remaining_sec", 0) or 0))
        else:
            for inst in self.instance_tracker.get_team_instances(str(team_id)):
                if int(inst.get("challenge_id", -1)) == int(challenge.id):
                    current_ttl = max(
                        0,
                        int(inst.get("expire_epoch", 0) or 0) - int(time.time()),
                    )
                    break

        return current_ttl

    def _count_team_instances_for_challenge(self, team_id: str, challenge_id: int) -> int:
        count = 0
        for inst in self.instance_tracker.get_team_instances(str(team_id)):
            if int(inst.get("challenge_id", -1)) == int(challenge_id):
                count += 1
        return count

    def _resolve_team_id(self) -> str:
        """Resolve current user's team id in a CTFd-version-tolerant way."""
        user = get_current_user()
        if not user:
            return ""

        team_id = getattr(user, "team_id", None)
        if team_id:
            return str(team_id)

        team_obj = getattr(user, "team", None)
        if team_obj and getattr(team_obj, "id", None):
            return str(team_obj.id)

        q_team = request.args.get("team_id")
        if q_team:
            return str(q_team)

        return ""

    def _is_admin_user(self) -> bool:
        """Best-effort admin check across CTFd versions."""
        user = get_current_user()
        if not user:
            return False

        if bool(getattr(user, "admin", False)):
            return True

        user_type = str(getattr(user, "type", "")).lower()
        if user_type == "admin":
            return True

        is_admin_attr = getattr(user, "is_admin", None)
        if callable(is_admin_attr):
            try:
                return bool(is_admin_attr())
            except Exception:
                return False

        return False

    def _register_routes(self):
        """Register plugin endpoints."""
        bp = Blueprint("orchestrator", __name__, url_prefix="/plugins/orchestrator")

        @bp.route("/start", methods=["POST"])
        @authed_only
        @require_team
        def start_instance():
            """
            Start a challenge instance for current team.
            
            Request body:
            {
                "challenge_id": 1,
                "ttl_min": 60
            }
            
            Response:
            {
                "ok": true,
                "instance": {
                    "url": "http://192.168.56.10:6100",
                    "port": 6100,
                    "team_id": "team-1",
                    "challenge": "web-01-sqli",
                    "expire_epoch": 1234567890,
                    "ttl_remaining_sec": 3600
                }
            }
            """
            try:
                data = request.get_json() or {}
                challenge_id = data.get("challenge_id")
                ttl_min_raw = data.get("ttl_min", 60)
                ttl_min = int(ttl_min_raw)
                team_id = self._resolve_team_id()

                if ttl_min < 5 or ttl_min > 240:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "invalid_ttl",
                                "detail": "ttl_min must be between 5 and 240 minutes",
                            }
                        ),
                        400,
                    )

                if not team_id:
                    return jsonify({"ok": False, "error": "team_not_found"}), 401

                if not challenge_id:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "missing_challenge_id",
                            }
                        ),
                        400,
                    )

                # Fetch challenge
                challenge = Challenges.query.get(challenge_id)
                if not challenge:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "challenge_not_found",
                            }
                        ),
                        404,
                    )

                # Check if orchestrator enabled for this challenge
                if not self._is_orchestrated_challenge(challenge):
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "challenge_not_orchestrated",
                                "note": "This challenge is static (no instances)",
                            }
                        ),
                        400,
                    )

                # Check team/global quota
                active_count = self.instance_tracker.count_active_instances(
                    team_id
                )
                max_active = int(os.getenv("ORCHESTRATOR_TEAM_MAX_ACTIVE", 10))
                if active_count >= max_active:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "team_quota_exceeded",
                                "active": active_count,
                                "max": max_active,
                            }
                        ),
                        409,
                    )

                # Check per-challenge quota for this team
                challenge_active_count = self._count_team_instances_for_challenge(team_id, int(challenge.id))
                challenge_max_active = int(os.getenv("ORCHESTRATOR_TEAM_CHALLENGE_MAX_ACTIVE", 2))
                if challenge_active_count >= challenge_max_active:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "challenge_quota_exceeded",
                                "challenge": challenge.name,
                                "active": challenge_active_count,
                                "max": challenge_max_active,
                            }
                        ),
                        409,
                    )

                # Call orchestrator API
                result = self.orchestrator_handler.start_instance(
                    challenge_name=challenge.name,
                    team_id=str(team_id),
                    ttl_min=ttl_min,
                )

                if not result.get("ok"):
                    logger.error(
                        f"Orchestrator start failed: {result.get('error')}"
                    )
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": result.get(
                                    "error", "orchestrator_error"
                                ),
                            }
                        ),
                        500,
                    )

                # Track instance in database
                instance_data = {
                    "team_id": str(team_id),
                    "challenge_id": challenge_id,
                    "challenge_name": challenge.name,
                    "url": result.get("url"),
                    "port": result.get("port"),
                    "expire_epoch": result.get("expire_epoch"),
                }
                self.instance_tracker.add_instance(instance_data)

                logger.info(
                    f"Instance started: team={team_id}, challenge={challenge.name}, port={result.get('port')}"
                )

                return (
                    jsonify(
                        {
                            "ok": True,
                            "instance": {
                                "url": result.get("url"),
                                "port": result.get("port"),
                                "team_id": str(team_id),
                                "challenge": challenge.name,
                                "expire_epoch": result.get("expire_epoch"),
                                "ttl_remaining_sec": result.get(
                                    "expire_epoch"
                                )
                                - int(time.time()),
                            },
                        }
                    ),
                    201,
                )

            except Exception as e:
                logger.exception(f"Error in start_instance: {e}")
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "internal_error",
                            "detail": str(e),
                        }
                    ),
                    500,
                )

        @bp.route("/stop", methods=["POST"])
        @authed_only
        @require_team
        def stop_instance():
            """Stop a running challenge instance."""
            try:
                data = request.get_json() or {}
                challenge_id = data.get("challenge_id")
                challenge_ref = data.get("challenge_name")
                team_id = self._resolve_team_id()

                if not team_id:
                    return jsonify({"ok": False, "error": "team_not_found"}), 401

                if not challenge_id and not challenge_ref:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "missing_challenge_reference",
                            }
                        ),
                        400,
                    )

                challenge = self._resolve_challenge_from_reference(challenge_id or challenge_ref)
                if not challenge:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "challenge_not_found",
                            }
                        ),
                        404,
                    )

                # Call orchestrator to stop
                result = self.orchestrator_handler.stop_instance(
                    challenge_name=challenge.name, team_id=str(team_id)
                )

                if not result.get("ok"):
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": result.get(
                                    "error", "orchestrator_error"
                                ),
                            }
                        ),
                        500,
                    )

                # Remove from tracker
                self.instance_tracker.remove_instance(team_id, int(challenge.id))

                logger.info(
                    f"Instance stopped: team={team_id}, challenge={challenge.name}"
                )

                return jsonify({"ok": True})

            except Exception as e:
                logger.exception(f"Error in stop_instance: {e}")
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "internal_error",
                            "detail": str(e),
                        }
                    ),
                    500,
                )

        @bp.route("/extend", methods=["POST"])
        @authed_only
        @require_team
        def extend_instance():
            """Extend a running challenge instance by 30 minutes."""
            try:
                data = request.get_json() or {}
                challenge_id = data.get("challenge_id")
                challenge_ref = data.get("challenge_name")
                team_id = self._resolve_team_id()

                if not team_id:
                    return jsonify({"ok": False, "error": "team_not_found"}), 401

                if not challenge_id and not challenge_ref:
                    return jsonify({"ok": False, "error": "missing_challenge_reference"}), 400

                challenge = self._resolve_challenge_from_reference(challenge_id or challenge_ref)
                if not challenge:
                    return jsonify({"ok": False, "error": "challenge_not_found"}), 404

                # Business rule: a single instance cannot exceed 60 minutes total TTL.
                add_seconds = 30 * 60
                max_seconds = 60 * 60
                current_ttl = 0

                row = self._find_status_row(str(team_id), challenge.name)
                if row and str(row.get("state", "")).strip().lower() == "running":
                    current_ttl = max(0, int(row.get("ttl_remaining_sec", 0) or 0))
                else:
                    for inst in self.instance_tracker.get_team_instances(str(team_id)):
                        if int(inst.get("challenge_id", -1)) == int(challenge.id):
                            current_ttl = max(0, int(inst.get("expire_epoch", 0) or 0) - int(time.time()))
                            break

                if current_ttl <= 0:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "instance_not_running",
                                "detail": "Cannot add time because the instance is not running.",
                            }
                        ),
                        409,
                    )

                if current_ttl + add_seconds > max_seconds:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "ttl_exceeds_max_1h",
                                "detail": "Cannot exceed 1 hour total TTL for one instance.",
                                "ttl_remaining_sec": current_ttl,
                                "max_ttl_sec": max_seconds,
                            }
                        ),
                        400,
                    )

                result = self.orchestrator_handler.extend_instance(
                    challenge_name=challenge.name,
                    team_id=str(team_id),
                    ttl_min=30,
                )

                if not result.get("ok"):
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": result.get("error", "orchestrator_error"),
                            }
                        ),
                        500,
                    )

                expire_epoch = int(result.get("expire_epoch", 0) or 0)
                if expire_epoch:
                    self.instance_tracker.update_instance_expire(team_id, int(challenge.id), expire_epoch)

                return jsonify({
                    "ok": True,
                    "expire_epoch": expire_epoch,
                    "ttl_remaining_sec": max(0, expire_epoch - int(time.time())) if expire_epoch else 0,
                })

            except Exception as e:
                logger.exception(f"Error in extend_instance: {e}")
                return (
                    jsonify({
                        "ok": False,
                        "error": "internal_error",
                        "detail": str(e),
                    }),
                    500,
                )

        @bp.route("/instances", methods=["GET"])
        @authed_only
        @require_team
        def list_instances():
            """List all active instances for current team."""
            try:
                team_id = self._resolve_team_id()
                if not team_id:
                    return jsonify({"ok": False, "error": "team_not_found"}), 401

                instances: List[Dict[str, Any]] = []
                player_host = os.getenv("ORCHESTRATOR_PLAYER_HOST", "192.168.56.10")
                for row in self._current_status_rows():
                    if str(row.get("team", "")) != str(team_id):
                        continue

                    state = str(row.get("state", "")).strip().lower()
                    if state and state != "running":
                        continue

                    challenge_name = str(row.get("challenge") or row.get("project") or "").strip()
                    challenge_obj = None
                    if challenge_name:
                        for ch in Challenges.query.all():
                            if normalize_slug(ch.name) == normalize_slug(challenge_name):
                                challenge_obj = ch
                                break

                    port = int(row.get("port", 0) or 0)
                    ttl_remaining_sec = max(0, int(row.get("ttl_remaining_sec", 0) or 0))
                    challenge_ref = str(challenge_obj.id if challenge_obj else challenge_name)
                    instance_url = f"http://{player_host}:{port}" if port else ""

                    open_href = instance_url
                    open_label = "Open Access"
                    connection_display = instance_url
                    access_mode = "web"
                    access_user = ""
                    access_password = ""
                    access_hint = ""

                    if challenge_obj:
                        access_hint_data = self._challenge_access_hint(challenge_obj)
                        access_user = str(access_hint_data.get("ssh_user", "") or "").strip()
                        access_password = str(access_hint_data.get("ssh_password", "") or "").strip()
                        access_hint = str(access_hint_data.get("hint", "") or "").strip()

                        access_methods = self._build_access_methods(
                            challenge_obj,
                            instance_url,
                            port,
                            "",
                        )
                        open_href = f"/plugins/orchestrator/launch?challenge_id={int(challenge_obj.id)}"
                        if access_methods:
                            primary = str(access_methods[0].get("type", "")).strip().lower()
                            if primary == "web":
                                open_href = str(access_methods[0].get("value", "") or open_href)
                                open_label = "Open Web Service"
                                access_mode = "web"
                                connection_display = str(access_methods[0].get("value", "") or instance_url)
                            elif primary == "ssh":
                                open_label = "View SSH Instructions"
                                access_mode = "ssh"
                                connection_display = str(access_methods[0].get("linux", "") or instance_url)
                            elif primary == "instruction":
                                open_label = "View Instructions"
                                access_mode = "instruction"
                                connection_display = "Instructions available"
                        if access_mode == "ssh" and not open_href:
                            open_href = f"/plugins/orchestrator/launch?challenge_id={int(challenge_obj.id)}"

                    instances.append(
                        {
                            "team_id": str(team_id),
                            "challenge_id": challenge_obj.id if challenge_obj else 0,
                            "challenge_name": challenge_obj.name if challenge_obj else challenge_name,
                            "challenge_ref": challenge_ref,
                            "port": port,
                            "url": instance_url,
                            "open_href": open_href,
                            "open_label": open_label,
                            "connection_display": connection_display,
                            "access_mode": access_mode,
                            "ssh_user": access_user,
                            "ssh_password": access_password,
                            "access_hint": access_hint,
                            "state": state or "running",
                            "ttl_remaining_sec": ttl_remaining_sec,
                            "expired": ttl_remaining_sec <= 0,
                        }
                    )

                return (
                    jsonify(
                        {
                            "ok": True,
                            "instances": instances,
                            "active_count": len(instances),
                        }
                    ),
                    200,
                )

            except Exception as e:
                logger.exception(f"Error in list_instances: {e}")
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "internal_error",
                            "detail": str(e),
                        }
                    ),
                    500,
                )

        @bp.route("/challenges", methods=["GET"])
        @authed_only
        @require_team
        def list_challenges():
            """List available challenges for quick start UI."""
            items = Challenges.query.order_by(Challenges.id.asc()).all()
            orchestrated = [ch for ch in items if self._is_orchestrated_challenge(ch)]
            return jsonify(
                {
                    "ok": True,
                    "challenges": [
                        {"id": ch.id, "name": ch.name}
                        for ch in orchestrated
                    ],
                }
            )

        @bp.route("/leaderboard/live", methods=["GET"])
        @authed_only
        def live_leaderboard():
            """Live active-instance counts grouped by team."""
            counts: Dict[str, int] = {}
            for row in self._current_status_rows():
                state = str(row.get("state", "")).strip().lower()
                if state != "running":
                    continue

                team_id = str(row.get("team", "")).strip()
                if not team_id:
                    continue

                counts[team_id] = counts.get(team_id, 0) + 1

            team_ids = [int(team_id) for team_id in counts.keys() if team_id.isdigit()]
            names = {
                str(t.id): t.name
                for t in Teams.query.filter(Teams.id.in_(team_ids)).all()
            } if team_ids else {}

            rows = [
                {
                    "team_id": team_id,
                    "team_name": names.get(team_id, team_id),
                    "active_instances": active,
                }
                for team_id, active in counts.items()
            ]
            rows.sort(key=lambda r: (-int(r["active_instances"]), str(r["team_name"]).lower()))

            return jsonify({"ok": True, "rows": rows})

        @bp.route("/launch", methods=["GET"])
        @authed_only
        @require_team
        def launch_from_challenge():
            """One-click launch endpoint for players (default TTL=60, no knobs)."""
            team_id = self._resolve_team_id()
            if not team_id:
                return "Team required", 401

            challenge_name = str(request.args.get("challenge", "")).strip()
            challenge_id = request.args.get("challenge_id")
            ttl_min = 60

            challenge = None
            if challenge_id and str(challenge_id).isdigit():
                challenge = Challenges.query.get(int(challenge_id))
            elif challenge_name:
                challenge = Challenges.query.filter_by(name=challenge_name).first()

            if not challenge:
                return "Challenge not found", 404

            if not self._is_orchestrated_challenge(challenge):
                return (
                    "This challenge does not use dynamic instance orchestration. "
                    "Use the challenge instructions in CTFd.",
                    400,
                )

            active_count = self.instance_tracker.count_active_instances(team_id)
            max_active = int(os.getenv("ORCHESTRATOR_TEAM_MAX_ACTIVE", 10))
            if active_count >= max_active:
                return (
                    f"Quota exceeded: {active_count}/{max_active} active instances for your team.",
                    409,
                )

            challenge_active_count = self._count_team_instances_for_challenge(team_id, int(challenge.id))
            challenge_max_active = int(os.getenv("ORCHESTRATOR_TEAM_CHALLENGE_MAX_ACTIVE", 2))
            if challenge_active_count >= challenge_max_active:
                return (
                    f"Challenge quota exceeded for {challenge.name}: {challenge_active_count}/{challenge_max_active} active instances.",
                    409,
                )

            result = self.orchestrator_handler.start_instance(
                challenge_name=challenge.name,
                team_id=str(team_id),
                ttl_min=ttl_min,
            )

            if not result.get("ok"):
                error_code = result.get("error", "orchestrator_error")
                detail = str(result.get("detail", "")).strip()
                msg = f"Launch failed: {error_code}"
                if detail:
                    msg += f"\n\nDetail: {detail}"
                return msg, 500

            instance_data = {
                "team_id": str(team_id),
                "challenge_id": challenge.id,
                "challenge_name": challenge.name,
                "url": result.get("url"),
                "port": result.get("port"),
                "expire_epoch": result.get("expire_epoch"),
            }
            
            # Some successful starts can return human-readable stdout only
            # (e.g. "Instance already running") without structured fields.
            url = str(result.get("url") or "").strip()
            port = result.get("port")
            expires = int(result.get("expire_epoch", int(time.time())))
            stdout = str(result.get("stdout", ""))

            if (not url or url.endswith(":0")) and stdout:
                m_url = re.search(r"URL\s*:\s*(https?://[^\s]+)", stdout)
                if m_url:
                    url = m_url.group(1)

            if (not port or int(port or 0) == 0) and url:
                m_port = re.search(r":(\d+)$", url)
                if m_port:
                    port = int(m_port.group(1))

            # Fallback to tracked active instance for this challenge/team.
            if not url or url.endswith(":0") or expires <= int(time.time()):
                for inst in self.instance_tracker.get_team_instances(str(team_id)):
                    if int(inst.get("challenge_id", -1)) == int(challenge.id):
                        url = str(inst.get("url") or url)
                        expires = int(inst.get("expire_epoch", expires))
                        port = int(inst.get("port", port or 0))
                        break

            instance_data["url"] = url
            instance_data["port"] = port
            instance_data["expire_epoch"] = expires
            self.instance_tracker.add_instance(instance_data)

            remaining = max(0, expires - int(time.time()))
            team_label = str(team_id)
            # Try to get team name from current user's team object first (most direct)
            try:
                user = get_current_user()
                if user:
                    user_team = getattr(user, "team", None)
                    if user_team:
                        team_name = getattr(user_team, "name", None)
                        if team_name:
                            team_label = str(team_name)
            except Exception:
                pass
            # Fallback: query Teams if not found via user
            if team_label == str(team_id) and str(team_id).isdigit():
                try:
                    team_obj = Teams.query.get(int(team_id))
                    if team_obj:
                        team_name = getattr(team_obj, "name", None)
                        if team_name:
                            team_label = str(team_name)
                except Exception:
                    pass

            access_methods = self._build_access_methods(challenge, url, port, stdout)
            if not access_methods:
                return (
                    "Launch completed, but no access method was resolved. "
                    "Please check challenge instructions.",
                    500,
                )

            web_method = next((m for m in access_methods if m.get("type") == "web"), None)
            redirect_url = web_method.get("value", "") if web_method else ""
            launch_description = self._build_launch_description(challenge, access_methods)
            access_hint = self._challenge_access_hint(challenge)

            credentials_block = ""
            cred_user = str(access_hint.get("ssh_user", "") or "").strip()
            cred_password = str(access_hint.get("ssh_password", "") or "").strip()
            if cred_user or cred_password:
                user_html = html.escape(cred_user) if cred_user else "-"
                pass_html = html.escape(cred_password) if cred_password else "-"
                credentials_block = f"""
<details class=\"method reveal\">
    <summary>Credentials (click to reveal)</summary>
    <div class=\"reveal-body\">
        <div class=\"kv-row\"><strong>Username:</strong> <code>{user_html}</code></div>
        <div class=\"kv-row\"><strong>Password:</strong> <code>{pass_html}</code></div>
    </div>
</details>
"""

            hint_block = ""
            hint_text = str(access_hint.get("hint", "") or "").strip()
            if hint_text:
                hint_block = f"""
<details class=\"method reveal hint\">
    <summary>Need a nudge? (click to reveal hint)</summary>
    <div class=\"reveal-body\">
        <pre>{html.escape(hint_text)}</pre>
    </div>
</details>
"""


            status_row = self._find_status_row(str(team_id), challenge.name)
            status_running = bool(
                status_row and str(status_row.get("state", "")).strip().lower() == "running"
            )
            status_ttl_remaining = (
                int(status_row.get("ttl_remaining_sec", 0) or 0) if status_row else max(0, expires - int(time.time()))
            )
            if not status_running and status_row is None:
                status_running = bool(url and not url.endswith(":0") and expires > int(time.time()))
            status_title = "Instance launched" if status_running else "Not started"
            status_class = "ok" if status_running else "warn"
            if not status_running:
                status_ttl_remaining = 0

            relaunch_href = f"/plugins/orchestrator/launch?challenge_id={int(challenge.id)}"
            relaunch_label = "Relaunch Instance" if status_running else "Start Instance"
            relaunch_block = f'<a class="btn btn-primary" id="relaunchBtn" href="{relaunch_href}" style="margin-right:8px;">{relaunch_label}</a>'

            method_blocks = []
            for idx, method in enumerate(access_methods):
                mtype = method.get("type")
                if mtype == "web":
                    method_blocks.append(
                        f"""
<div class=\"method\">
    <h3>Web Access</h3>
    <a class=\"btn btn-primary\" href=\"{html.escape(method.get('value', ''))}\" target=\"_blank\" rel=\"noopener\">Open Challenge Instance</a>
</div>
"""
                    )
                elif mtype == "ssh":
                    linux_raw = str(method.get("linux", "") or "")
                    windows_raw = str(method.get("windows", "") or "")
                    linux_cmd = html.escape(linux_raw)
                    windows_cmd = html.escape(windows_raw)
                    if linux_raw.strip() == windows_raw.strip():
                        method_blocks.append(
                            f"""
<div class=\"method\">
    <h3>SSH Access</h3>
    <p class=\"note\">Click the command card to copy it.</p>
    <div class=\"cmd-row\">
        <label>Command</label>
        <div class=\"cmd-copy-card\" role=\"button\" tabindex=\"0\" aria-label=\"Copy SSH command\" data-copy=\"{linux_cmd}\">{linux_cmd}<span class=\"copy-icon\" aria-hidden=\"true\"></span><span class=\"copy-ok\">COPIED</span></div>
    </div>
</div>
"""
                        )
                    else:
                        method_blocks.append(
                            f"""
<div class=\"method\">
    <h3>SSH Access</h3>
    <p class=\"note\">Click either command card to copy it.</p>
    <div class=\"cmd-row\">
        <label>Linux/macOS</label>
        <div class=\"cmd-copy-card\" role=\"button\" tabindex=\"0\" aria-label=\"Copy Linux command\" data-copy=\"{linux_cmd}\">{linux_cmd}<span class=\"copy-icon\" aria-hidden=\"true\"></span><span class=\"copy-ok\">COPIED</span></div>
    </div>
    <div class=\"cmd-row\">
        <label>Windows (PowerShell)</label>
        <div class=\"cmd-copy-card\" role=\"button\" tabindex=\"0\" aria-label=\"Copy Windows command\" data-copy=\"{windows_cmd}\">{windows_cmd}<span class=\"copy-icon\" aria-hidden=\"true\"></span><span class=\"copy-ok\">COPIED</span></div>
    </div>
</div>
"""
                        )
                else:
                    method_blocks.append(
                        f"""
<div class=\"method\">
    <h3>Instructions</h3>
    <pre>{html.escape(method.get('value', ''))}</pre>
</div>
"""
                    )

            ttl_m = status_ttl_remaining // 60
            ttl_s = status_ttl_remaining % 60
            ttl_formatted = f"{ttl_m}m {ttl_s:02d}s" if status_ttl_remaining > 0 else "—"

            html_page = f"""
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Instance Ready</title>
    <style>
        :root {{
            --bg: #070d16;
            --card: #101a2a;
            --surface: #0d1624;
            --text: #e6edf7;
            --muted: #9aa8bc;
            --ok: #34d399;
            --bad: #f87171;
            --warn: #f59e0b;
            --btn-primary: #2563eb;
            --btn-secondary: #0f1a2a;
            --ring: rgba(59, 130, 246, 0.18);
            --line: #2a3548;
        }}

        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background:
                radial-gradient(800px 520px at 8% -10%, rgba(59,130,246,0.2), transparent 60%),
                radial-gradient(860px 540px at 100% -15%, rgba(16,185,129,0.12), transparent 62%),
                var(--bg);
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            color: var(--text);
            padding: 24px;
        }}

        .card {{
            width: min(680px, 96vw);
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 12px 30px rgba(2, 6, 23, 0.42);
            overflow: hidden;
        }}

        .head {{
            padding: 22px 24px;
            border-bottom: 1px solid var(--line);
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 999px;
            background: var(--ok);
            box-shadow: 0 0 0 8px var(--ring);
            animation: pulse 1.8s infinite ease-in-out;
        }}

        .dot.bad {{
            background: var(--bad);
            box-shadow: 0 0 0 8px rgba(185, 28, 28, 0.12);
        }}

        .dot.warn {{
            background: var(--warn);
            box-shadow: 0 0 0 8px rgba(245, 158, 11, 0.12);
        }}

        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 var(--ring); }}
            70% {{ box-shadow: 0 0 0 12px rgba(37,99,235,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(37,99,235,0); }}
        }}

        .title {{
            margin: 0;
            font-size: 1.55rem;
            letter-spacing: 0.2px;
        }}

        .body {{ padding: 20px 24px 24px; }}

        .meta {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 18px;
        }}

        .pill {{
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 10px 12px;
        }}

        .k {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; }}
        .v {{ margin-top: 6px; font-size: 1rem; font-weight: 650; color: var(--text); word-break: break-word; }}

        .note {{
            color: var(--muted);
            margin: 2px 0 16px;
            line-height: 1.45;
        }}

        .method {{
            border: 1px solid var(--line);
            background: var(--surface);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 12px;
        }}

        .method h3 {{ margin: 0 0 8px; }}

        .reveal {{
            padding: 0;
            overflow: hidden;
            background: #0f1a2a;
        }}

        .reveal summary {{
            list-style: none;
            cursor: pointer;
            padding: 14px;
            font-weight: 700;
            background: linear-gradient(135deg, #14243a, #1c2d45);
        }}

        .reveal.hint summary {{
            background: linear-gradient(135deg, #2a1f10, #302515);
        }}

        .reveal summary::-webkit-details-marker {{ display: none; }}

        .reveal-body {{
            border-top: 1px solid var(--line);
            padding: 12px 14px 14px;
        }}

        .kv-row {{ margin-bottom: 8px; }}
        .kv-row code {{
            background: #0d1f35;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 2px 6px;
        }}

        .reveal-card {{
            padding: 0;
            overflow: hidden;
        }}

        .reveal-toggle {{
            width: 100%;
            border: 0;
            background: linear-gradient(135deg, #14243a, #1c2d45);
            color: var(--text);
            font-weight: 700;
            text-align: left;
            padding: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }}

        .reveal-card.hint .reveal-toggle {{
            background: linear-gradient(135deg, #2a1f10, #302515);
        }}

        .reveal-cta {{
            color: var(--muted);
            font-weight: 600;
            font-size: 0.9rem;
        }}

        .reveal-content {{
            border-top: 1px solid var(--line);
            padding: 12px 14px 14px;
            background: #0f1a2a;
        }}

        .kv-row {{ margin-bottom: 8px; }}
        .kv-row code {{
            background: #0b1524;
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 2px 6px;
        }}

        .cmd-row {{ margin-bottom: 10px; }}
        .cmd-row label {{ color: var(--muted); font-size: 0.85rem; display: block; margin-bottom: 6px; }}
        pre {{
            margin: 0 0 8px;
            background: #0a1524;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px;
            overflow-x: auto;
        }}

        .cmd-copy-card {{
            position: relative;
            background: #0a1524;
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 15px 48px 15px 14px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
            font-size: 1.02rem;
            font-weight: 600;
            cursor: pointer;
            user-select: all;
            min-height: 56px;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            line-height: 1.35;
            word-break: break-word;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            transition: background 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
        }}

        .cmd-copy-card:hover {{
            border-color: #3d5f93;
            background: #111f34;
        }}

        .cmd-copy-card.copied {{
            border-color: #22c55e;
            background: #0f2318;
            box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.18) inset;
        }}

        .cmd-copy-card:focus {{
            outline: 2px solid #9db4df;
            outline-offset: 1px;
        }}

        .copy-icon {{
            position: absolute;
            right: 14px;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            border: 2px solid #9fb0c6;
            border-radius: 3px;
            opacity: 0.95;
            pointer-events: none;
        }}

        .copy-ok {{
            position: absolute;
            right: 40px;
            top: 50%;
            color: #86efac;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            opacity: 0;
            transform: translateY(-50%);
            transition: opacity 0.14s ease, transform 0.14s ease;
            pointer-events: none;
        }}

        .cmd-copy-card.copied .copy-ok {{
            opacity: 1;
            transform: translateY(-50%);
        }}

        .btn {{
            text-decoration: none;
            border-radius: 10px;
            padding: 11px 16px;
            font-weight: 700;
            letter-spacing: 0.2px;
            transition: transform 0.15s ease, opacity 0.15s ease;
            border: 1px solid transparent;
            display: inline-block;
        }}

        .btn:hover {{ transform: translateY(-1px); }}

        .btn-primary {{
            color: #fff;
            background: var(--btn-primary);
            border-color: var(--btn-primary);
        }}

        .btn-secondary {{
            color: var(--text);
            background: var(--btn-secondary);
            border-color: var(--line);
        }}

        .btn-row {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 4px;
        }}

        .tiny {{
            margin-top: 16px;
            color: #5a6a82;
            font-size: 0.8rem;
            text-align: center;
        }}

        @media (max-width: 740px) {{
            .meta {{ grid-template-columns: 1fr; }}
            .btn {{ width: 100%; text-align: center; }}
        }}
    </style>
</head>
<body>
    <section class=\"card\">
        <header class=\"head\">
            <span class=\"dot {status_class}\" id=\"statusDot\" aria-hidden=\"true\"></span>
            <h1 class=\"title\" id=\"statusTitle\">{status_title}</h1>
        </header>

        <div class=\"body\">
            <div class=\"meta\">
                <div class=\"pill\">
                    <div class=\"k\">Challenge</div>
                    <div class=\"v\">{html.escape(challenge.name)}</div>
                </div>
                <div class=\"pill\">
                    <div class=\"k\">Team</div>
                    <div class=\"v\">{html.escape(team_label)}</div>
                </div>
                <div class=\"pill\">
                    <div class=\"k\">TTL Remaining</div>
                    <div class=\"v\" id=\"ttlValue\">{ttl_formatted}</div>
                </div>
            </div>

            <p class=\"note\" id=\"launchDescription\">{html.escape(launch_description)}</p>

            {credentials_block}

            {hint_block}

            {''.join(method_blocks)}

            <div class=\"btn-row\">{relaunch_block}<a class=\"btn btn-secondary\" href=\"/challenges\">Back to Challenges</a></div>

            <p class=\"tiny\" id=\"autoLine\">Redirecting in <span id=\"countdown\">60</span>s... <a href=\"#\" id=\"stayHere\" style=\"color:var(--btn-primary); margin-left:6px;\">stay here</a></p>
        </div>
    </section>

    <script>
        function toggleReveal(contentId) {{
            const content = document.getElementById(contentId);
            const button = document.getElementById(contentId + '-btn');
            if (!content || !button) return;

            const hidden = content.hasAttribute('hidden');
            if (hidden) {{
                content.removeAttribute('hidden');
                button.setAttribute('aria-expanded', 'true');
            }} else {{
                content.setAttribute('hidden', 'hidden');
                button.setAttribute('aria-expanded', 'false');
            }}
        }}

        function copyCmdText(text) {{
            const value = String(text || '');
            if (!value) return Promise.resolve(false);

            if (navigator.clipboard && window.isSecureContext) {{
                return navigator.clipboard.writeText(value)
                    .then(() => true)
                    .catch(() => false);
            }}

            // Fallback for non-secure origins (common on local VM HTTP setups).
            const area = document.createElement('textarea');
            area.value = value;
            area.setAttribute('readonly', 'readonly');
            area.style.position = 'fixed';
            area.style.opacity = '0';
            area.style.pointerEvents = 'none';
            document.body.appendChild(area);
            area.select();

            let ok = false;
            try {{
                ok = document.execCommand('copy');
            }} catch (_e) {{
                ok = false;
            }} finally {{
                document.body.removeChild(area);
            }}

            return Promise.resolve(ok);
        }}

        function markCopied(card, ok) {{
            if (!card || !ok) return;
            card.classList.add('copied');
            window.setTimeout(() => card.classList.remove('copied'), 900);
        }}

        document.addEventListener('click', (ev) => {{
            const card = ev.target.closest('.cmd-copy-card');
            if (!card) return;
            copyCmdText(card.getAttribute('data-copy') || card.innerText || '').then((ok) => markCopied(card, ok));
        }});

        document.addEventListener('keydown', (ev) => {{
            const card = ev.target.closest('.cmd-copy-card');
            if (!card) return;
            if (ev.key === 'Enter' || ev.key === ' ') {{
                ev.preventDefault();
                copyCmdText(card.getAttribute('data-copy') || card.innerText || '').then((ok) => markCopied(card, ok));
            }}
        }});

        const statusEndpoint = '/plugins/orchestrator/instance-status?challenge_id={challenge.id}';
        const statusDot = document.getElementById('statusDot');
        const statusTitle = document.getElementById('statusTitle');
        const ttlValue = document.getElementById('ttlValue');
        const launchDescription = document.getElementById('launchDescription');
        const originalLaunchDescription = launchDescription.textContent;

        let n = 60;
        let cancelled = false;
        const el = document.getElementById('countdown');
        const stayLink = document.getElementById('stayHere');
        const autoLine = document.getElementById('autoLine');

        async function refreshInstanceState() {{
            try {{
                const res = await fetch(statusEndpoint);
                const data = await res.json();
                if (!data.ok) {{
                    return;
                }}

                const running = Boolean(data.running);
                statusDot.className = 'dot ' + (running ? 'ok' : 'warn');
                statusTitle.textContent = running ? 'Instance launched' : 'Not started';
                const remSec = Math.max(0, Number(data.ttl_remaining_sec || 0));
                const remM = Math.floor(remSec / 60);
                const remS = remSec % 60;
                ttlValue.textContent = remSec > 0 ? `${{remM}}m ${{String(remS).padStart(2, '0')}}s` : '—';
                if (running) {{
                    launchDescription.textContent = originalLaunchDescription;
                }} else {{
                    launchDescription.textContent = 'The instance is not currently running. Use the launch button or return to the challenge page to relaunch it.';
                }}
            }} catch (err) {{
                // Keep the rendered state if live refresh temporarily fails.
            }}
        }}

        if (!{json.dumps(bool(redirect_url))}) {{
            autoLine.textContent = 'No automatic redirect for this access mode.';
        }} else {{
            stayLink.addEventListener('click', (ev) => {{
                ev.preventDefault();
                cancelled = true;
                el.textContent = 'paused';
                stayLink.textContent = 'auto-redirect paused';
                stayLink.style.pointerEvents = 'none';
                stayLink.style.opacity = '0.8';
            }});

            const timer = setInterval(() => {{
                if (cancelled) {{
                    clearInterval(timer);
                    return;
                }}
                n -= 1;
                if (n <= 0) {{
                    clearInterval(timer);
                    window.location.href = {json.dumps(redirect_url)};
                    return;
                }}
                el.textContent = String(n);
            }}, 1000);
        }}

        refreshInstanceState();
        setInterval(refreshInstanceState, 10000);
    </script>
</body>
</html>
"""
            return html_page

        @bp.route("/btn/<int:challenge_id>", methods=["GET"])
        def launch_button_page(challenge_id):
            """
            Clickable launch button for players.
            Checks if user is authed + in a team; redirects to login if not.
            Redirects straight to the launch page.
            """
            # Check auth: if user not logged in, redirect to login
            user = get_current_user()
            if not user or not getattr(user, "type", None):
                # Redirect to login with 'next' to return to this page after login
                return f"""
                <script>
                    window.location.href = '/login?next=/plugins/orchestrator/btn/{challenge_id}';
                </script>
                Not authorized. Redirecting to login...
                """
            
            # Check if user is in a team (required for instance launch)
            team_id = getattr(user, "team_id", None) or (getattr(user, "team", None) and getattr(user.team, "id", None))
            if not team_id:
                return """
                <div style="font-family: sans-serif; padding: 20px; color: #c33;">
                    <h2>Team Required</h2>
                    <p>You must be part of a team to launch challenge instances.</p>
                    <p><a href="/teams">Create or join a team</a></p>
                </div>
                """, 403

            challenge = Challenges.query.get(challenge_id)
            if not challenge:
                return "Challenge not found", 404

            if not self._is_orchestrated_challenge(challenge):
                return (
                    """
                <div style="font-family: sans-serif; padding: 20px; color: #444;">
                    <h2>Static Challenge</h2>
                    <p>This challenge does not require a dynamic instance launch.</p>
                    <p>Please follow the challenge description/instructions directly.</p>
                    <p><a href="/challenges">Back to challenges</a></p>
                </div>
                """,
                    400,
                )

            return redirect(f"/plugins/orchestrator/launch?challenge_id={challenge_id}", code=302)

        @bp.route("/ui", methods=["GET"])
        @authed_only
        @require_team
        def ops_ui():
            """Admin/dev operations UI with start/stop and live TTL."""
            if not self._is_admin_user():
                return "Forbidden", 403
            return render_template_string(
                UI_TEMPLATE,
                team_name="Admin",
                initial_message="",
                initial_kind="ok",
            )

        @bp.route("/dashboard", methods=["GET"])
        @authed_only
        @require_team
        def team_dashboard():
            """Player team dashboard for instance lifecycle management."""
            user = get_current_user()
            team_name = "Team"
            initial_message = str(request.args.get("msg", "") or "").strip()
            initial_kind = str(request.args.get("kind", "ok") or "ok").strip().lower()
            if initial_kind not in {"ok", "err"}:
                initial_kind = "ok"
            try:
                if getattr(user, "team", None) and getattr(user.team, "name", None):
                    team_name = str(user.team.name)
                else:
                    team_id = self._resolve_team_id()
                    if team_id and str(team_id).isdigit():
                        t = Teams.query.get(int(team_id))
                        if t and getattr(t, "name", None):
                            team_name = str(t.name)
            except Exception:
                # Keep dashboard available even if team name lookup fails.
                pass

            return render_template_string(
                UI_TEMPLATE,
                team_name=team_name,
                initial_message=initial_message,
                initial_kind=initial_kind,
            )

        @bp.route("/stop-ui", methods=["GET"])
        @authed_only
        @require_team
        def stop_instance_ui():
            """Stop instance from dashboard card without relying on frontend JS."""
            team_id = self._resolve_team_id()
            challenge_ref = str(request.args.get("challenge_ref", "") or "").strip()

            if not team_id:
                return self._dashboard_redirect("err", "Team not found")
            if not challenge_ref:
                return self._dashboard_redirect("err", "Missing challenge reference")

            challenge = self._resolve_challenge_from_reference(challenge_ref)
            if not challenge:
                return self._dashboard_redirect("err", "Challenge not found")

            result = self.orchestrator_handler.stop_instance(
                challenge_name=challenge.name,
                team_id=str(team_id),
            )
            if not result.get("ok"):
                detail = str(result.get("detail", "") or result.get("error", "orchestrator_error"))
                return self._dashboard_redirect("err", f"Kill failed: {detail}")

            self.instance_tracker.remove_instance(team_id, int(challenge.id))
            return self._dashboard_redirect("ok", f"Instance stopped for {challenge.name}.")

        @bp.route("/extend-ui", methods=["GET"])
        @authed_only
        @require_team
        def extend_instance_ui():
            """Extend instance from dashboard card without relying on frontend JS."""
            team_id = self._resolve_team_id()
            challenge_ref = str(request.args.get("challenge_ref", "") or "").strip()

            if not team_id:
                return self._dashboard_redirect("err", "Team not found")
            if not challenge_ref:
                return self._dashboard_redirect("err", "Missing challenge reference")

            challenge = self._resolve_challenge_from_reference(challenge_ref)
            if not challenge:
                return self._dashboard_redirect("err", "Challenge not found")

            add_seconds = 30 * 60
            max_seconds = 60 * 60
            current_ttl = self._resolve_current_instance_ttl(str(team_id), challenge)

            if current_ttl <= 0:
                return self._dashboard_redirect("err", "Cannot add time: instance is not running.")

            if current_ttl + add_seconds > max_seconds:
                return self._dashboard_redirect("err", "Cannot exceed 1 hour total TTL for one instance.")

            result = self.orchestrator_handler.extend_instance(
                challenge_name=challenge.name,
                team_id=str(team_id),
                ttl_min=30,
            )
            if not result.get("ok"):
                detail = str(result.get("detail", "") or result.get("error", "orchestrator_error"))
                return self._dashboard_redirect("err", f"Add time failed: {detail}")

            expire_epoch = int(result.get("expire_epoch", 0) or 0)
            if expire_epoch:
                self.instance_tracker.update_instance_expire(team_id, int(challenge.id), expire_epoch)

            return self._dashboard_redirect("ok", f"Added 30m on {challenge.name}.")

        @bp.route("/instance-status", methods=["GET"])
        @authed_only
        @require_team
        def instance_status():
            """Return live status for the current team/challenge from the manager."""
            team_id = self._resolve_team_id()
            challenge_id = request.args.get("challenge_id", "")
            if not team_id or not str(challenge_id).isdigit():
                return jsonify({"ok": False, "error": "invalid_request"}), 400

            challenge = Challenges.query.get(int(challenge_id))
            if not challenge:
                return jsonify({"ok": False, "error": "challenge_not_found"}), 404

            row = self._find_status_row(str(team_id), challenge.name)
            if not row:
                for inst in self.instance_tracker.get_team_instances(str(team_id)):
                    if int(inst.get("challenge_id", -1)) == int(challenge.id):
                        ttl_remaining = max(0, int(inst.get("expire_epoch", 0) or 0) - int(time.time()))
                        return jsonify(
                            {
                                "ok": True,
                                "running": ttl_remaining > 0,
                                "state": "running" if ttl_remaining > 0 else "down",
                                "ttl_remaining_sec": ttl_remaining,
                                "challenge_id": challenge.id,
                                "challenge_name": challenge.name,
                                "team_id": str(team_id),
                            }
                        )

                return jsonify(
                    {
                        "ok": True,
                        "running": False,
                        "state": "down",
                        "ttl_remaining_sec": 0,
                        "challenge_id": challenge.id,
                        "challenge_name": challenge.name,
                    }
                )

            ttl_remaining = int(row.get("ttl_remaining_sec", 0) or 0)
            state = str(row.get("state", "down")).strip().lower()
            return jsonify(
                {
                    "ok": True,
                    "running": state == "running",
                    "state": state if state else ("running" if ttl_remaining > 0 else "down"),
                    "ttl_remaining_sec": max(0, ttl_remaining),
                    "port": int(row.get("port", 0) or 0),
                    "challenge_id": challenge.id,
                    "challenge_name": challenge.name,
                    "team_id": str(team_id),
                }
            )

        @bp.route("/sync", methods=["POST"])
        def sync_challenges_endpoint():
            """
            Sync challenges from Git to CTFd without needing API token.
            Uses shared secret (ORCHESTRATOR_SIGNING_SECRET) for auth.
            
            Usage:
                curl -X POST http://192.168.56.10/plugins/orchestrator/sync \
                  -H "X-Orchestrator-Secret: ChangeMe-Orchestrator-Signing-Secret"
            """
            secret = os.getenv("ORCHESTRATOR_SIGNING_SECRET", "")
            provided_secret = request.headers.get("X-Orchestrator-Secret", "")

            if not secret or provided_secret != secret:
                return jsonify({"ok": False, "error": "unauthorized"}), 401

            try:
                # Query all challenges
                challenges = Challenges.query.all()
                synced = 0

                for ch in challenges:
                    if not self._is_orchestrated_challenge(ch):
                        continue
                    # Generate direct launch link for launch-mode connection_info
                    button_url = f"{request.host_url.rstrip('/')}/plugins/orchestrator/launch?challenge_id={ch.id}"
                    
                    # Update connection_info with button link (if not already set)
                    if not ch.connection_info or "/plugins/orchestrator/launch?challenge_id=" not in ch.connection_info:
                        ch.connection_info = button_url
                        synced += 1

                db.session.commit()

                logger.info(f"Sync completed: updated {synced}/{len(challenges)} challenges with button links")
                return jsonify({
                    "ok": True,
                    "synced": synced,
                    "total": len(challenges),
                    "message": f"Updated {synced} challenge(s) with launch button links"
                }), 200

            except Exception as e:
                logger.exception(f"Error in sync_challenges_endpoint: {e}")
                return jsonify({"ok": False, "error": str(e)}), 500

        self.app.register_blueprint(bp)

    def _is_orchestrated_challenge(self, challenge) -> bool:
        """
        Determine whether challenge should use dynamic orchestration.

        Rule: only challenges backed by a spawnable runtime definition
        (docker-compose.yml in /vagrant/challenges, including nested layouts)
        are considered orchestrated.
        """
        try:
            challenge_name = str(getattr(challenge, "name", "") or "")
            return self._is_spawnable_challenge_name(challenge_name)
        except Exception:
            return False

