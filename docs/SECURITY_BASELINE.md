# Security Baseline

This repository currently targets a demo/training deployment model.

## Implemented baseline

- Orchestrator API service runs with stricter systemd sandbox options.
- Orchestrator API token is externalized through `/etc/ctf/orchestrator.env`.
- API request signing is supported with HMAC-SHA256.
- API rate-limiting supports both client-level and team-level limits.
- Team active-instance quota is enforced before start actions.
- Centralized audit logging is written to `/var/log/ctf/orchestrator-audit.log`.
- CTFd webhook trigger endpoint is available at `/ctfd/event`.
- API now binds on localhost and is exposed through an nginx reverse proxy.
- Security preflight workflow runs on PRs touching security-related files.
- Vault-based secret overrides are supported through `ansible/vars/vault.yml`.

## Security preflight

Script: `scripts/security-preflight.py`

Default behavior:

- warns when development secrets are still present
- does not fail the pipeline in non-strict mode

Strict mode:

```bash
SECURITY_STRICT=1 python scripts/security-preflight.py
```

## Operational requirements

1. Create `ansible/vars/vault.yml` from `ansible/vars/vault.example.yml`.
2. Encrypt the vault file with Ansible Vault and provide the vault password during deployment.
3. Rotate all development defaults before any shared/staging/production use.
4. Configure CI preflight in strict mode for protected branches.
