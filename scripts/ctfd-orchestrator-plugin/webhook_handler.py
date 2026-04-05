"""
Webhook Handler for Orchestrator API Communication

Handles HMAC-SHA256 signing and communication with orchestrator endpoints.
"""

import hashlib
import hmac
import json
import logging
import re
import time
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger("ctfd.orchestrator_webhook")


class OrchestratorWebhookHandler:
    """Communication layer with Player Instance Orchestrator API."""

    def __init__(
        self,
        api_url: str,
        api_token: str,
        signing_secret: str,
        webhook_token: str,
    ):
        """
        Initialize orchestrator handler.
        
        Args:
            api_url: Base URL of orchestrator API (e.g., http://127.0.0.1:8181)
            api_token: X-Orchestrator-Token value
            signing_secret: Secret for HMAC-SHA256 signatures
            webhook_token: X-CTFd-Webhook-Token value
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.signing_secret = signing_secret
        self.webhook_token = webhook_token
        self.session = requests.Session()

    def _generate_signature(self, body: str) -> tuple[str, str]:
        """Generate HMAC-SHA256 signature for request body."""
        ts = str(int(time.time()))
        message = f"{ts}.{body}".encode("utf-8")
        signature = hmac.new(
            self.signing_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()
        return ts, signature

    def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Dict[str, Any],
        sign: bool = True,
    ) -> Dict[str, Any]:
        """
        Make signed HTTP request to orchestrator.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (e.g., /start, /stop)
            payload: Request body (dict)
            sign: Whether to sign request (POST operations)
        
        Returns:
            Response JSON dict
        """
        url = f"{self.api_url}{endpoint}"
        body_str = json.dumps(payload)
        headers = {
            "Content-Type": "application/json",
            "X-Orchestrator-Token": self.api_token,
            "X-CTFd-Webhook-Token": self.webhook_token,
        }

        # Add signature for POST requests
        if method.upper() == "POST" and sign and self.signing_secret:
            ts, sig = self._generate_signature(body_str)
            headers["X-Signature-Timestamp"] = ts
            headers["X-Signature"] = sig

        try:
            logger.debug(
                f"{method} {url} | Payload: {payload}"
            )

            if method.upper() == "POST":
                resp = self.session.post(url, data=body_str, headers=headers, timeout=10)
            else:
                resp = self.session.get(url, headers=headers, timeout=10)

            logger.debug(f"Status: {resp.status_code} | Response: {resp.text}")

            if resp.status_code >= 400:
                logger.error(
                    f"Orchestrator error: {resp.status_code} {resp.text}"
                )
                return {
                    "ok": False,
                    "error": f"http_{resp.status_code}",
                    "detail": resp.text,
                }

            data = resp.json()
            return data

        except requests.exceptions.RequestException as e:
            logger.exception(f"Request failed: {e}")
            return {
                "ok": False,
                "error": "connection_error",
                "detail": str(e),
            }
        except json.JSONDecodeError as e:
            logger.exception(f"JSON decode error: {e}")
            return {
                "ok": False,
                "error": "invalid_response",
                "detail": str(e),
            }

    def start_instance(
        self,
        challenge_name: str,
        team_id: str,
        ttl_min: int = 60,
        port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Start a challenge instance via orchestrator.
        
        Returns:
        {
            "ok": true,
            "url": "http://192.168.56.10:6100",
            "port": 6100,
            "expire_epoch": 1234567890
        }
        """
        payload = {
            "challenge": challenge_name,
            "team": team_id,
            "ttl_min": ttl_min,
        }
        if port:
            payload["port"] = port

        result = self._make_request("POST", "/start", payload)

        # Extract useful fields if successful
        if result.get("ok"):
            stdout = result.get("stdout", "").strip()
            # Parse output to extract URL and port
            # Format: "CHALLENGE=name TEAM_ID=1 PROJECT=proj PORT=6100 EXPIRE_EPOCH=123456"
            parsed = self._parse_manager_output(stdout)
            result.update(parsed)

        return result

    def stop_instance(
        self, challenge_name: str, team_id: str
    ) -> Dict[str, Any]:
        """Stop a running challenge instance."""
        payload = {"challenge": challenge_name, "team": team_id}
        return self._make_request("POST", "/stop", payload)

    def extend_instance(
        self,
        challenge_name: str,
        team_id: str,
        ttl_min: int = 30,
    ) -> Dict[str, Any]:
        """Extend a running challenge instance."""
        payload = {"challenge": challenge_name, "team": team_id, "ttl_min": ttl_min}
        result = self._make_request("POST", "/extend", payload)

        if result.get("ok"):
            stdout = result.get("stdout", "").strip()
            parsed = self._parse_manager_output(stdout)
            result.update(parsed)

        return result

    def cleanup_instances(self) -> Dict[str, Any]:
        """Cleanup expired instances."""
        return self._make_request("POST", "/cleanup", {})

    def get_status(self) -> Dict[str, Any]:
        """Fetch live instance status from the manager."""
        return self._make_request("GET", "/status", {}, sign=False)

    def _parse_manager_output(self, stdout: str) -> Dict[str, Any]:
        """
        Parse orchestrator manager output to extract instance details.
        
        Format:
        CHALLENGE=web-01 TEAM_ID=1 PROJECT=web_01_team_1 PORT=6100 EXPIRE_EPOCH=1234567890
        """
        parsed: Dict[str, Any] = {}
        for line in stdout.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Human-readable format fallback:
            # URL     : http://192.168.56.10:6100
            if line.lower().startswith("url") and ":" in line:
                url_val = line.split(":", 1)[1].strip()
                if url_val:
                    parsed["url"] = url_val
                    m = re.search(r":(\d+)$", url_val)
                    if m:
                        parsed["port"] = m.group(1)

            for kv in line.split():
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    parsed[k.lower()] = v

        port = int(parsed.get("port", 0)) if str(parsed.get("port", "0")).isdigit() else 0
        url = str(parsed.get("url", "")).strip()
        if not url:
            url = f"http://192.168.56.10:{port}"

        # Map to standard response fields
        return {
            "port": port,
            "url": url,
            "expire_epoch": int(parsed.get("expire_epoch", 0)) if str(parsed.get("expire_epoch", "0")).isdigit() else 0,
        }
