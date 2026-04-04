"""
Instance Tracker

In-memory tracking of active challenge instances per team.
Allows quick lookups and quota enforcement.
"""

import logging
import time
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
        with self._lock:
            if team_id not in self._instances:
                self._instances[team_id] = []
            self._instances[team_id].append(instance_data)
            self._ensure_stats(team_id)["starts_total"] += 1
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
                logger.debug(
                    f"Removed instance: team={team_id}, challenge_id={challenge_id}"
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
