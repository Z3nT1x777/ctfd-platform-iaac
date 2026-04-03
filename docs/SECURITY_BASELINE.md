# Security Baseline

This repository currently targets a demo/training deployment model.

## Implemented baseline

- Orchestrator API service runs with stricter systemd sandbox options.
- Orchestrator API token is externalized through `/etc/ctf/orchestrator.env`.
- API rate-limiting support is available in runtime configuration.
- Security preflight workflow runs on PRs touching security-related files.

## Security preflight

Script: `scripts/security-preflight.py`

Default behavior:

- warns when development secrets are still present
- does not fail the pipeline in non-strict mode

Strict mode:

```bash
SECURITY_STRICT=1 python scripts/security-preflight.py
```

## Recommended next hardening steps

1. Move sensitive vars to Ansible Vault.
2. Rotate default credentials before shared/staging deployments.
3. Restrict orchestrator API bind to localhost and expose through a controlled proxy if needed.
4. Add request signing and per-team quotas.
5. Add centralized audit logging for start/stop/cleanup actions.
