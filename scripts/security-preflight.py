#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VARS_FILE = REPO_ROOT / "ansible" / "vars" / "main.yml"
VAULT_FILE = REPO_ROOT / "ansible" / "vars" / "vault.yml"
MONITORING_TEMPLATE = REPO_ROOT / "ansible" / "templates" / "docker-compose-monitoring.yml.j2"

DEFAULTS = {
    "DB_ROOT_PASSWORD": "RootPassword123!",
    "DB_PASSWORD": "CTFdPassword123!",
    "orchestrator_api_token": "ChangeMe-Orchestrator-Token",
    "orchestrator_signing_secret": "ChangeMe-Orchestrator-Signing-Secret",
    "orchestrator_ctfd_webhook_token": "ChangeMe-CTFd-Webhook-Token",
    "grafana_admin_password": "admin",
}


def vault_is_present() -> bool:
    if not VAULT_FILE.exists():
        return False

    text = VAULT_FILE.read_text(encoding="utf-8", errors="ignore")
    # Encrypted files start with this marker; plain text files are also accepted.
    return bool(text.strip())


def main() -> int:
    if not VARS_FILE.exists():
        print("ERROR: vars file not found")
        return 1

    content = VARS_FILE.read_text(encoding="utf-8")
    failures = []
    strict_mode = os.environ.get("SECURITY_STRICT", "0") == "1"
    has_vault = vault_is_present()

    for key, default in DEFAULTS.items():
        needle = f'{key}: "{default}"'
        if needle in content:
            failures.append(f"{key} is still using a development default ({default!r})")

    # Also check for hardcoded Grafana password in monitoring template (belt-and-suspenders)
    if MONITORING_TEMPLATE.exists():
        template_content = MONITORING_TEMPLATE.read_text(encoding="utf-8")
        if "GF_SECURITY_ADMIN_PASSWORD=admin" in template_content:
            failures.append(
                "docker-compose-monitoring.yml.j2 has hardcoded GF_SECURITY_ADMIN_PASSWORD=admin"
            )

    if failures:
        print("Security preflight warnings:")
        for failure in failures:
            print(f" - {failure}")
        if has_vault:
            print("Vault file detected at ansible/vars/vault.yml (overrides may be active).")
            print("Confirm vaulted values replace development defaults during deployment.")
            return 0

        print("Update ansible/vars/main.yml or move secrets to Vault before production deployment.")
        if strict_mode:
            return 1
        return 0

    print("Security preflight passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
