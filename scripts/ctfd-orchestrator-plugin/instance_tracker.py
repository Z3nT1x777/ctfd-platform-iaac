"""
Instance Tracker

In-memory tracking of active challenge instances per team.
Allows quick lookups and quota enforcement.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any
from threading import Lock

logger = logging.getLogger("ctfd.orchestrator_tracker")


class InstanceTracker:
    """Track active instances per team."""

    def __init__(self):
        """Initialize tracker."""
        self._instances: Dict[str, List[Dict[str, Any]]] = {}
        self._stats: Dict[str, Dict[str, int]] = {}
        self._lock = Lock()
        self._state_file = Path(
            os.getenv(
                "ORCHESTRATOR_INSTANCE_STATE_FILE",
                "/opt/ctf/orchestrator/state/instances.json",
            )
        )
        self._load_state()

    def _load_state(self) -> None:
        try:
            if not self._state_file.exists():
                return
            payload = json.loads(self._state_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self._instances = {
                    str(team_id): [inst for inst in instances if isinstance(inst, dict)]
                    for team_id, instances in (payload.get("instances") or {}).items()
                    if isinstance(instances, list)
                }
                self._stats = {
                    str(team_id): {
                        "starts_total": int(stats.get("starts_total", 0) or 0),
                        "stops_total": int(stats.get("stops_total", 0) or 0),
                        "expired_total": int(stats.get("expired_total", 0) or 0),
                    }
                    for team_id, stats in (payload.get("stats") or {}).items()
                    if isinstance(stats, dict)
                }
        except Exception:
            logger.exception("Failed to load instance tracker state")

    def _save_state(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "instances": self._instances,
                "stats": self._stats,
            }
            tmp_path = self._state_file.with_suffix(self._state_file.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
            tmp_path.replace(self._state_file)
        except Exception:
            logger.exception("Failed to save instance tracker state")

    def _ensure_stats(self, team_id: str) -> Dict[str, int]:
        if team_id not in self._stats:
            self._stats[team_id] = {
                "starts_total": 0,
                "stops_total": 0,
                "expired_total": 0,
            }
        return self._stats[team_id]

    def add_instance(self, instance_data: Dict[str, Any]) -> None:
        """
        Add active instance to tracker.
        
        Args:
            instance_data: {
                "team_id": "team-1",
                "challenge_id": 1,
                "challenge_name": "web-01",
                "url": "http://...:6100",
                "port": 6100,
                "expire_epoch": 1234567890
            }
        """
        team_id = str(instance_data.get("team_id"))
        challenge_id = instance_data.get("challenge_id")
        with self._lock:
            if team_id not in self._instances:
                self._instances[team_id] = []

            # Replace existing entry for same challenge to keep tracker consistent.
            if challenge_id is not None:
                self._instances[team_id] = [
                    inst
                    for inst in self._instances[team_id]
                    if inst.get("challenge_id") != challenge_id
                ]

            self._instances[team_id].append(instance_data)
            self._ensure_stats(team_id)["starts_total"] += 1
            self._save_state()
            logger.debug(
                f"Added instance: team={team_id}, challenge={instance_data.get('challenge_name')}"
            )

    def remove_instance(self, team_id: str, challenge_id: int) -> None:
        """Remove instance from tracker."""
        team_id = str(team_id)
        with self._lock:
            if team_id in self._instances:
                before = len(self._instances[team_id])
                self._instances[team_id] = [
                    inst
                    for inst in self._instances[team_id]
                    if inst.get("challenge_id") != challenge_id
                ]
                removed = before - len(self._instances[team_id])
                if removed > 0:
                    self._ensure_stats(team_id)["stops_total"] += removed
                    self._save_state()
                logger.debug(
                    f"Removed instance: team={team_id}, challenge_id={challenge_id}"
                )

    def update_instance_expire(self, team_id: str, challenge_id: int, expire_epoch: int) -> None:
        """Update the expiration timestamp for a tracked instance."""
        team_id = str(team_id)
        with self._lock:
            if team_id not in self._instances:
                return

            updated = False
            for inst in self._instances[team_id]:
                if inst.get("challenge_id") == challenge_id:
                    inst["expire_epoch"] = int(expire_epoch)
                    updated = True

            if updated:
                self._save_state()
                logger.debug(
                    f"Updated instance expiration: team={team_id}, challenge_id={challenge_id}, expire_epoch={expire_epoch}"
                )

    def get_team_instances(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get active instances for team.
        
        Filters out expired instances automatically.
        """
        team_id = str(team_id)
        now = int(time.time())
        with self._lock:
            all_instances = self._instances.get(team_id, [])
            # Filter out expired
            active = [
                inst
                for inst in all_instances
                if inst.get("expire_epoch", 0) > now
            ]
            # Update tracker to remove expired
            if len(active) < len(all_instances):
                self._instances[team_id] = active
                self._ensure_stats(team_id)["expired_total"] += len(all_instances) - len(active)
                self._save_state()
            return active

    def count_active_instances(self, team_id: str) -> int:
        """Count active (non-expired) instances for team."""
        return len(self.get_team_instances(team_id))

    def cleanup_expired(self) -> Dict[str, int]:
        """
        Remove all expired instances.
        
        Returns:
            {"teams_cleaned": 5, "instances_removed": 12}
        """
        now = int(time.time())
        removed_count = 0

        with self._lock:
            for team_id in list(self._instances.keys()):
                before = len(self._instances[team_id])
                self._instances[team_id] = [
                    inst
                    for inst in self._instances[team_id]
                    if inst.get("expire_epoch", 0) > now
                ]
                after = len(self._instances[team_id])
                removed_count += before - after
                if before > after:
                    self._ensure_stats(team_id)["expired_total"] += before - after

                # Remove team key if no instances left
                if not self._instances[team_id]:
                    del self._instances[team_id]

            self._save_state()

        return {
            "teams_cleaned": len(
                [t for t in self._instances if self._instances[t]]
            ),
            "instances_removed": removed_count,
        }

    def leaderboard(self) -> List[Dict[str, Any]]:
        """Return real-time leaderboard rows for team activity."""
        now = int(time.time())
        rows: List[Dict[str, Any]] = []
        with self._lock:
            for team_id in set(list(self._instances.keys()) + list(self._stats.keys())):
                active_instances = [
                    inst for inst in self._instances.get(team_id, []) if inst.get("expire_epoch", 0) > now
                ]
                stats = self._ensure_stats(team_id)
                rows.append(
                    {
                        "team_id": team_id,
                        "active_instances": len(active_instances),
                        "starts_total": stats["starts_total"],
                        "stops_total": stats["stops_total"],
                        "expired_total": stats["expired_total"],
                    }
                )

        rows.sort(
            key=lambda row: (
                row["active_instances"],
                row["starts_total"],
                -row["stops_total"],
            ),
            reverse=True,
        )
        return rows
