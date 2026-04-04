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

from flask import Blueprint, request, jsonify, render_template_string
from CTFd.models import Challenges, Teams, db
from CTFd.utils.decorators import authed_only, require_team
from CTFd.utils.user import get_current_user

from .webhook_handler import OrchestratorWebhookHandler
from .instance_tracker import InstanceTracker
from .access_profiles import build_access_methods, load_access_hint_from_dir, normalize_slug

logger = logging.getLogger("ctfd.orchestrator_plugin")

UI_TEMPLATE = """
<!doctype html>
<html>
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>CTFd Instance Ops</title>
    <style>
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 14px; }
        .row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
        input, select, button { padding: 8px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border-bottom: 1px solid #eee; text-align: left; padding: 8px; }
        code { background: #f6f6f6; padding: 2px 6px; border-radius: 4px; }
        @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <h1>CTFd Player Instance Control</h1>
    <p>Start or stop team instances, see TTL countdown, and follow live team activity.</p>
    <div class=\"grid\">
        <div class=\"card\">
            <h3>Instance Controls</h3>
            <div class=\"row\">
                <select id=\"challenge\"></select>
                <input id=\"ttl\" type=\"number\" value=\"60\" min=\"5\" max=\"240\" />
            </div>
            <div class=\"row\">
                <button id=\"startBtn\">Start Challenge</button>
                <button id=\"stopBtn\">Stop Challenge</button>
                <button id=\"refreshBtn\">Refresh</button>
            </div>
            <div id=\"message\"></div>
            <h4>Team Active Instances</h4>
            <table>
                <thead><tr><th>Challenge</th><th>URL</th><th>TTL</th></tr></thead>
                <tbody id=\"instances\"></tbody>
            </table>
        </div>
        <div class=\"card\">
            <h3>Live Activity Leaderboard</h3>
            <table>
                <thead><tr><th>Rank</th><th>Team</th><th>Active</th><th>Starts</th><th>Stops</th><th>Expired</th></tr></thead>
                <tbody id=\"leaderboard\"></tbody>
            </table>
        </div>
    </div>

    <script>
        const fmt = (sec) => {
            if (sec <= 0) return 'expired';
            const m = Math.floor(sec / 60);
            const s = sec % 60;
            return `${m}m ${s}s`;
        };

        async function fetchChallenges() {
            const res = await fetch('/plugins/orchestrator/challenges');
            const data = await res.json();
            const sel = document.getElementById('challenge');
            sel.innerHTML = '';
            (data.challenges || []).forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.id} - ${c.name}`;
                sel.appendChild(opt);
            });
        }

        async function startInstance() {
            const challenge_id = Number(document.getElementById('challenge').value);
            const ttl_min = Number(document.getElementById('ttl').value || 60);
            const res = await fetch('/plugins/orchestrator/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ challenge_id, ttl_min })
            });
            const data = await res.json();
            document.getElementById('message').textContent = data.ok
                ? `Instance started at ${data.instance.url}`
                : `Error: ${data.error || 'unknown'}`;
            await refreshInstances();
            await refreshLeaderboard();
        }

        async function stopInstance() {
            const challenge_id = Number(document.getElementById('challenge').value);
            const res = await fetch('/plugins/orchestrator/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ challenge_id })
            });
            const data = await res.json();
            document.getElementById('message').textContent = data.ok
                ? 'Instance stopped'
                : `Error: ${data.error || 'unknown'}`;
            await refreshInstances();
            await refreshLeaderboard();
        }

        async function refreshInstances() {
            const res = await fetch('/plugins/orchestrator/instances');
            const data = await res.json();
            const body = document.getElementById('instances');
            body.innerHTML = '';
            (data.instances || []).forEach(inst => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${inst.challenge_name || '-'}</td><td><a href="${inst.url}" target="_blank">${inst.url}</a></td><td>${fmt(inst.ttl_remaining_sec || 0)}</td>`;
                body.appendChild(tr);
            });
        }

        async function refreshLeaderboard() {
            const res = await fetch('/plugins/orchestrator/leaderboard/live');
            const data = await res.json();
            const body = document.getElementById('leaderboard');
            body.innerHTML = '';
            (data.rows || []).forEach((row, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${idx + 1}</td><td>${row.team_name || row.team_id}</td><td>${row.active_instances}</td><td>${row.starts_total}</td><td>${row.stops_total}</td><td>${row.expired_total}</td>`;
                body.appendChild(tr);
            });
        }

        document.getElementById('startBtn').addEventListener('click', startInstance);
        document.getElementById('stopBtn').addEventListener('click', stopInstance);
        document.getElementById('refreshBtn').addEventListener('click', async () => {
            await refreshInstances();
            await refreshLeaderboard();
        });

        fetchChallenges();
        refreshInstances();
        refreshLeaderboard();
        setInterval(async () => {
            await refreshInstances();
            await refreshLeaderboard();
        }, 10000);
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
        return load_access_hint_from_dir(challenge_dir) if challenge_dir else {"mode": "auto", "ssh_user": "", "instructions": "", "container_port": "", "type": ""}

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

                # Check team quota
                active_count = self.instance_tracker.count_active_instances(
                    team_id
                )
                max_active = int(os.getenv("ORCHESTRATOR_TEAM_MAX_ACTIVE", 3))
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
                team_id = self._resolve_team_id()

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
                self.instance_tracker.remove_instance(team_id, challenge_id)

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

        @bp.route("/instances", methods=["GET"])
        @authed_only
        @require_team
        def list_instances():
            """List all active instances for current team."""
            try:
                team_id = self._resolve_team_id()
                if not team_id:
                    return jsonify({"ok": False, "error": "team_not_found"}), 401

                instances = self.instance_tracker.get_team_instances(team_id)

                # Add remaining time to each
                now = int(time.time())
                for inst in instances:
                    inst["ttl_remaining_sec"] = max(
                        0, inst.get("expire_epoch", 0) - now
                    )
                    inst["expired"] = inst["ttl_remaining_sec"] <= 0

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
            """Real-time activity leaderboard from instance lifecycle events."""
            rows = self.instance_tracker.leaderboard()
            team_ids = [r["team_id"] for r in rows]
            names = {
                str(t.id): t.name
                for t in Teams.query.filter(Teams.id.in_(team_ids)).all()
            } if team_ids else {}

            for row in rows:
                row["team_name"] = names.get(str(row["team_id"]), str(row["team_id"]))

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
            ttl_min_raw = str(request.args.get("ttl_min", "60")).strip()
            ttl_min = int(ttl_min_raw) if ttl_min_raw.isdigit() else 60

            if ttl_min < 5 or ttl_min > 240:
                return "Invalid timer: ttl_min must be between 5 and 240 minutes", 400

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
            max_active = int(os.getenv("ORCHESTRATOR_TEAM_MAX_ACTIVE", 3))
            if active_count >= max_active:
                return (
                    f"Quota exceeded: {active_count}/{max_active} active instances for your team.",
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
            if str(team_id).isdigit():
                team_obj = Teams.query.get(int(team_id))
                if team_obj and getattr(team_obj, "name", None):
                    team_label = str(team_obj.name)

            access_methods = self._build_access_methods(challenge, url, port, stdout)
            if not access_methods:
                return (
                    "Launch completed, but no access method was resolved. "
                    "Please check challenge instructions.",
                    500,
                )

            web_method = next((m for m in access_methods if m.get("type") == "web"), None)
            redirect_url = web_method.get("value", "") if web_method else ""

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
                    linux_cmd = html.escape(method.get("linux", ""))
                    windows_cmd = html.escape(method.get("windows", ""))
                    method_blocks.append(
                        f"""
<div class=\"method\">
    <h3>SSH Access</h3>
    <p class=\"note\">Use one of these commands:</p>
    <div class=\"cmd-row\">
        <label>Linux/macOS</label>
        <pre id=\"cmd-linux-{idx}\">{linux_cmd}</pre>
        <button class=\"btn btn-secondary\" onclick=\"copyCmd('cmd-linux-{idx}')\">Copy</button>
    </div>
    <div class=\"cmd-row\">
        <label>Windows (PowerShell)</label>
        <pre id=\"cmd-win-{idx}\">{windows_cmd}</pre>
        <button class=\"btn btn-secondary\" onclick=\"copyCmd('cmd-win-{idx}')\">Copy</button>
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

            html_page = f"""
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Instance Ready</title>
    <style>
        :root {{
            --bg-a: #0b1220;
            --bg-b: #0f1f2f;
            --card: #0f1726;
            --text: #ecf2ff;
            --muted: #a8b4ca;
            --ok: #23c47e;
            --btn-a: #16a34a;
            --btn-b: #22c55e;
            --btn-secondary-a: #1e293b;
            --btn-secondary-b: #334155;
            --ring: rgba(35, 196, 126, 0.35);
            --line: rgba(255, 255, 255, 0.08);
        }}

        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background:
                radial-gradient(1200px 700px at 10% -20%, #123a6a 0%, transparent 55%),
                radial-gradient(900px 600px at 95% 120%, #1a5b5f 0%, transparent 55%),
                linear-gradient(135deg, var(--bg-a), var(--bg-b));
            font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            color: var(--text);
            padding: 24px;
        }}

        .card {{
            width: min(680px, 96vw);
            background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
            border: 1px solid var(--line);
            border-radius: 18px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45);
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

        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 var(--ring); }}
            70% {{ box-shadow: 0 0 0 12px rgba(35,196,126,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(35,196,126,0); }}
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
            background: rgba(255,255,255,0.03);
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
            background: rgba(255,255,255,0.02);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 12px;
        }}

        .method h3 {{ margin: 0 0 8px; }}

        .cmd-row {{ margin-bottom: 10px; }}
        .cmd-row label {{ color: var(--muted); font-size: 0.85rem; display: block; margin-bottom: 6px; }}
        pre {{
            margin: 0 0 8px;
            background: #0b1322;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px;
            overflow-x: auto;
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
            color: #06260f;
            background: linear-gradient(90deg, var(--btn-a), var(--btn-b));
            border-color: rgba(255,255,255,0.18);
        }}

        .btn-secondary {{
            color: var(--text);
            background: linear-gradient(90deg, var(--btn-secondary-a), var(--btn-secondary-b));
            border-color: var(--line);
        }}

        .tiny {{
            margin-top: 12px;
            color: var(--muted);
            font-size: 0.88rem;
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
            <span class=\"dot\" aria-hidden=\"true\"></span>
            <h1 class=\"title\">Instance launched</h1>
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
                    <div class=\"v\">{remaining} seconds</div>
                </div>
            </div>

            <p class=\"note\">Access is generated from runtime signals and challenge metadata. Commands are copy-ready for Linux and Windows terminals.</p>

            {''.join(method_blocks)}

            <a class=\"btn btn-secondary\" href=\"/challenges\">Back to Challenges</a>

            <p class=\"tiny\" id=\"autoLine\">Auto-redirecting in <span id=\"countdown\">8</span>s... <a href=\"#\" id=\"stayHere\" style=\"color:#9ad1ff; margin-left:6px;\">stay here</a></p>
        </div>
    </section>

    <script>
        function copyCmd(id) {{
            const text = document.getElementById(id).innerText;
            navigator.clipboard.writeText(text).catch(() => {{}});
        }}

        let n = 8;
        let cancelled = false;
        const el = document.getElementById('countdown');
        const stayLink = document.getElementById('stayHere');
        const autoLine = document.getElementById('autoLine');

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
            Returns HTML with a launch button that POST to /start endpoint.
            Query params (optional): ttl_min (default 60)
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

            ttl_min_raw = str(request.args.get("ttl_min", "60")).strip()
            ttl_min = int(ttl_min_raw) if ttl_min_raw.isdigit() else 60

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

            html = f"""
<!doctype html>
<html>
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Launch {challenge.name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 500px;
            text-align: center;
        }}
        h2 {{
            color: #333;
            margin-bottom: 12px;
            font-size: 28px;
        }}
        .ch-name {{
            color: #667eea;
            font-weight: bold;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        p {{
            color: #666;
            line-height: 1.6;
            margin-bottom: 8px;
        }}
        .settings {{
            background: #f5f5f5;
            border-radius: 8px;
            padding: 16px;
            margin: 24px 0;
            text-align: left;
        }}
        .form-group {{
            margin-bottom: 12px;
        }}
        label {{
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
            font-size: 14px;
        }}
        input[type="number"] {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        input[type="number"]:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 12px;
            width: 100%;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }}
        .btn:active {{
            transform: translateY(0);
        }}
        .loading {{ display: none; }}
        .btn.loading {{
            opacity: 0.7;
            cursor: not-allowed;
        }}
        .loading-text {{ margin-left: 8px; }}
        .error {{
            background: #fee;
            color: #c33;
            padding: 12px;
            border-radius: 4px;
            margin: 12px 0;
            display: none;
        }}
        .success {{
            background: #efe;
            color: #3c3;
            padding: 12px;
            border-radius: 4px;
            margin: 12px 0;
            display: none;
        }}
    </style>
</head>
<body>
    <div class=\"container\">
        <h2>Ready to start?</h2>
        <div class=\"ch-name\">{challenge.name}</div>
        <p>Click the button below to launch your personal instance</p>
        
        <div class=\"settings\">
            <div class=\"form-group\">
                <label for=\"ttl\">Time to Live (minutes):</label>
                <input type=\"number\" id=\"ttl\" value=\"{ttl_min}\" min=\"5\" max=\"240\" />
            </div>
        </div>

        <button class=\"btn\" id=\"launchBtn\" onclick=\"launchInstance()\">
            <span id=\"btnText\">Launch Challenge</span>
            <span class=\"loading\" id=\"btnLoading\"><span class=\"spinner\">⏳</span><span class=\"loading-text\">Launching...</span></span>
        </button>

        <div class=\"error\" id=\"errorMsg\"></div>
        <div class=\"success\" id=\"successMsg\"></div>

        <p style=\"margin-top: 24px; font-size: 12px; color: #999;\">
            Your instance will be available for the specified TTL duration.
        </p>
    </div>

    <script>
        function launchInstance() {{
            const ttl = Number(document.getElementById('ttl').value || 60);
            const errorMsg = document.getElementById('errorMsg');
            const successMsg = document.getElementById('successMsg');

            errorMsg.style.display = 'none';
            successMsg.style.display = 'none';

            if (ttl < 5 || ttl > 240) {{
                errorMsg.textContent = 'TTL must be between 5 and 240 minutes';
                errorMsg.style.display = 'block';
                return;
            }}

            // Use GET launch endpoint to avoid browser-side POST auth/CSRF pitfalls.
            window.location.href = '/plugins/orchestrator/launch?challenge_id={challenge_id}&ttl_min=' + ttl;
        }}

        // Manual launch button - user clicks to start
    </script>
</body>
</html>
"""
            return html

        @bp.route("/ui", methods=["GET"])
        @authed_only
        @require_team
        def ops_ui():
            """Admin/dev operations UI with start/stop and live TTL."""
            if not self._is_admin_user():
                return "Forbidden", 403
            return render_template_string(UI_TEMPLATE)

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
                    # Generate button link for launch-mode connection_info
                    button_url = f"{request.host_url.rstrip('/')}/plugins/orchestrator/btn/{ch.id}?ttl_min=60"
                    
                    # Update connection_info with button link (if not already set)
                    if not ch.connection_info or "btn/" not in ch.connection_info:
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
