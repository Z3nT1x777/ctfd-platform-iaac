"""
CTFd Orchestrator Integration Plugin

Handles challenge instance lifecycle:
- Intercepts challenge start/stop events from CTFd UI
- Creates isolated Docker instances via orchestrator API
- Manages per-team quotas and TTL tracking
- Provides UI updates with instance URLs and remaining time
"""

import logging
import os
import time
from typing import Any
from urllib.parse import quote

from flask import Blueprint, request, jsonify, render_template_string
from CTFd.models import Challenges, Teams
from CTFd.utils.decorators import authed_only, require_team
from CTFd.utils.user import get_current_user

from .webhook_handler import OrchestratorWebhookHandler
from .instance_tracker import InstanceTracker

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
                "ORCHESTRATOR_API_URL", "http://127.0.0.1:8181"
            ),
            api_token=os.getenv("ORCHESTRATOR_API_TOKEN", ""),
            signing_secret=os.getenv("ORCHESTRATOR_SIGNING_SECRET", ""),
            webhook_token=os.getenv("ORCHESTRATOR_WEBHOOK_TOKEN", ""),
        )
        self.instance_tracker = InstanceTracker()
        self._register_routes()
        logger.info("CTFd Orchestrator Plugin initialized")

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
                ttl_min = int(data.get("ttl_min", 60))
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
            return jsonify(
                {
                    "ok": True,
                    "challenges": [
                        {"id": ch.id, "name": ch.name}
                        for ch in items
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

            challenge = None
            if challenge_id and str(challenge_id).isdigit():
                challenge = Challenges.query.get(int(challenge_id))
            elif challenge_name:
                challenge = Challenges.query.filter_by(name=challenge_name).first()

            if not challenge:
                return "Challenge not found", 404

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
                return f"Launch failed: {result.get('error', 'orchestrator_error')}", 500

            instance_data = {
                "team_id": str(team_id),
                "challenge_id": challenge.id,
                "challenge_name": challenge.name,
                "url": result.get("url"),
                "port": result.get("port"),
                "expire_epoch": result.get("expire_epoch"),
            }
            self.instance_tracker.add_instance(instance_data)

            url = result.get("url") or ""
            expires = int(result.get("expire_epoch", int(time.time())))
            remaining = max(0, expires - int(time.time()))

            html = f"""
<!doctype html>
<html>
<head><meta charset=\"utf-8\" /><title>Challenge Launched</title></head>
<body style=\"font-family: system-ui, sans-serif; margin: 24px;\">
  <h2>Instance launched</h2>
  <p><b>Challenge:</b> {challenge.name}</p>
  <p><b>Team:</b> {team_id}</p>
  <p><b>TTL remaining:</b> {remaining} seconds</p>
  <p><a href=\"{url}\" target=\"_blank\">Open your challenge instance</a></p>
  <p><a href=\"/challenges\">Back to challenges</a></p>
</body>
</html>
"""
            return html

        @bp.route("/btn/<int:challenge_id>", methods=["GET"])
        def launch_button_page(challenge_id):
            """
            Clickable launch button for players (no auth required for button page).
            Returns HTML with a launch button that POST to /start endpoint.
            Query params (optional): ttl_min (default 60), auto_redirect=true
            """
            ttl_min_raw = str(request.args.get("ttl_min", "60")).strip()
            ttl_min = int(ttl_min_raw) if ttl_min_raw.isdigit() else 60
            auto_redirect = request.args.get("auto_redirect", "").lower() == "true"

            challenge = Challenges.query.get(challenge_id)
            if not challenge:
                return "Challenge not found", 404

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
        async function launchInstance() {{
            const ttl = Number(document.getElementById('ttl').value || 60);
            const btn = document.getElementById('launchBtn');
            const btnText = document.getElementById('btnText');
            const btnLoading = document.getElementById('btnLoading');
            const errorMsg = document.getElementById('errorMsg');
            const successMsg = document.getElementById('successMsg');

            if (ttl < 5 || ttl > 240) {{
                errorMsg.textContent = 'TTL must be between 5 and 240 minutes';
                errorMsg.style.display = 'block';
                return;
            }}

            btn.disabled = true;
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline';

            try {{
                const response = await fetch('/plugins/orchestrator/start', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ challenge_id: {challenge_id}, ttl_min: ttl }})
                }});

                const data = await response.json();

                if (!response.ok || !data.ok) {{
                    throw new Error(data.error || 'Launch failed');
                }}

                successMsg.textContent = 'Instance launched successfully! Redirecting...';
                successMsg.style.display = 'block';

                setTimeout(() => {{
                    window.location.href = data.instance.url;
                }}, 2000);

            }} catch (error) {{
                errorMsg.textContent = 'Error: ' + error.message;
                errorMsg.style.display = 'block';
                btn.disabled = false;
                btnText.style.display = 'inline';
                btnLoading.style.display = 'none';
            }}
        }}

        // Optional: Support auto-redirect on page load
        {'window.onload = () => { launchInstance(); };' if auto_redirect else '// Manual launch button only'}
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

        self.app.register_blueprint(bp)

    def _is_orchestrated_challenge(self, challenge) -> bool:
        """
        Check if challenge is configured for orchestrator.
        
        Criteria:
        - Has 'orchestrated' flag set (future: CTFd-level config)
        - For now: all challenges with Docker Compose are eligible
        """
        # Future: Check challenge.description or custom field for orchestration flag
        # For MVP: assume all challenges are orchestrated (admins filter manually)
        return True
