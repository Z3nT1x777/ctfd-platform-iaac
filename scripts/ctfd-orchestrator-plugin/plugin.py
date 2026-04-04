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
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

from flask import Blueprint, request, jsonify, render_template_string
from CTFd.models import db, Challenges, Users, Teams
from CTFd.utils.decorators import authed_only, require_team
from sqlalchemy.exc import SQLAlchemyError

from .webhook_handler import OrchestratorWebhookHandler
from .instance_tracker import InstanceTracker

logger = logging.getLogger("ctfd.orchestrator_plugin")


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

    def _register_routes(self):
        """Register plugin endpoints."""
        bp = Blueprint("orchestrator", __name__, url_prefix="/plugins/orchestrator")

        @bp.route("/start", methods=["POST"])
        @authed_only
        @require_team(redirect_url="/challenges")
        def start_instance(team_id=None):
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

                # Get team_id from session (CTFd provides this)
                if not team_id:
                    team_obj = Teams.query.filter_by(
                        id=request.args.get("team_id")
                    ).first()
                    if not team_obj:
                        return (
                            jsonify(
                                {
                                    "ok": False,
                                    "error": "team_not_found",
                                }
                            ),
                            401,
                        )
                    team_id = team_obj.id

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
        @require_team(redirect_url="/challenges")
        def stop_instance(team_id=None):
            """Stop a running challenge instance."""
            try:
                data = request.get_json() or {}
                challenge_id = data.get("challenge_id")

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
        @require_team(redirect_url="/challenges")
        def list_instances(team_id=None):
            """List all active instances for current team."""
            try:
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
