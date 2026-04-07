# CTF Platform Custom

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Vagrant](https://img.shields.io/badge/Vagrant-2.4%2B-blue)](https://www.vagrantup.com/)
[![Ansible](https://img.shields.io/badge/Ansible-2.14%2B-red)](https://www.ansible.com/)

## Overview

This repository is the single source of truth for the custom CTF platform deployment and operations.

Included capabilities:

- **Infrastructure:** Reproducible VM provisioning with Vagrant and Ansible
- **Platform:** CTFd deployment on Docker Compose with centralized configuration
- **Challenges:** Templates by family (`web`, `osint`, `sandbox`, `reverse`, `pwn`) with CI validation
- **Orchestration:** Per-team challenge instance management with automatic TTL-based cleanup
- **API Security:** HMAC-SHA256 request signing, per-team rate limiting (30 req/min), per-client rate limiting (60 req/min)
- **Quotas:** Per-team instance quotas (max 3 concurrent by default, configurable)
- **Audit Logging:** Centralized JSON audit logs to `/var/log/ctf/orchestrator-audit.log` with event tracking
- **Webhooks:** CTFd event trigger endpoint (`POST /ctfd/event`) for automated instance lifecycle
- **Web UI:** Dashboard for orchestrator operations with team instance controls
- **Secrets Management:** Ansible Vault support for production secret overrides (passwords, API keys, signing secrets)
- **Reverse Proxy:** nginx ingress for controlled API exposure with X-Forwarded-For client tracking
- **Validation:** Security preflight checks in CI and git hooks
- **Player Launch UX:** One-click launch pages in CTFd with access-aware rendering (web, SSH commands, instructions)

## Technology Stack

| Component | Technology |
|-----------|------------|
| Provisioning | Vagrant + VirtualBox |
| Configuration | Ansible |
| Runtime | Docker + Compose |
| CTF Platform | CTFd |
| Validation CI | GitHub Actions |
| Orchestration | Bash manager + Python API + systemd timer |

## Quick Start

```bash
git clone https://github.com/USERNAME/ctfd-platform-custom.git
cd ctfd-platform-custom
vagrant up --provision
```

Access points after provisioning:

- CTFd: http://192.168.56.10
- CTFd (forwarded): http://localhost:8000
- Orchestrator UI (admin/dev): http://192.168.56.10:8181/ui

## Challenge Authoring Workflow

Use family templates from [challenges/_templates](challenges/_templates).

Windows example:

```powershell
./scripts/new-challenge.ps1 -Name web-01-test -Family web
./scripts/validate-challenge.ps1 -Path challenges/web-01-test
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

Editable values in the first command:
- <span style="color:#ff6b6b"><code>web-01-test</code></span> = challenge slug/name
- <span style="color:#4dabf7"><code>web</code></span> = challenge family

Linux/macOS example:

```bash
bash ./scripts/new-challenge.sh web-01-test --family web
bash ./scripts/validate-challenge.sh challenges/web-01-test
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

Detailed guide: [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md)

## Security Notes

The platform ships with security defaults enabled and keeps the sensitive parts configurable.

- HMAC signing, rate limits, instance quotas, and webhook validation are built in.
- Production secrets are handled through Ansible Vault.
- Security details, threat mapping, and deployment guidance live in [docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md) and [docs/VAULT_SETUP.md](docs/VAULT_SETUP.md).
- Troubleshooting notes remain available in [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [docs/REPO_CONTENT_GUIDELINES.md](docs/REPO_CONTENT_GUIDELINES.md) | Defines what belongs in the core platform, operations layer, and challenge layer | Maintainers, contributors |
| [docs/CUSTOM_REPO_WORKFLOW.md](docs/CUSTOM_REPO_WORKFLOW.md) | Standard Git workflow for this single custom repository | Maintainers, platform teams |
| [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md) | Challenge authoring and deployment workflow, template structure, validation rules | CTF authors, challenge creators |
| [docs/PLAYER_INSTANCE_ORCHESTRATOR.md](docs/PLAYER_INSTANCE_ORCHESTRATOR.md) | Orchestrator API reference, endpoints, HMAC request signing, team quotas, audit logs | Developers, DevOps, API consumers |

### Optional Guides

These are useful, but they are not required for day-1 deployment:

- [docs/WORKFLOW_PRIORITIES.md](docs/WORKFLOW_PRIORITIES.md)
- [docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md)
- [docs/VAULT_SETUP.md](docs/VAULT_SETUP.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- [docs/TROUBLESHOOTING.md#operations-command-cookbook](docs/TROUBLESHOOTING.md#operations-command-cookbook)
- [docs/MONITORING.md](docs/MONITORING.md)
- [docs/CTFD_ORCHESTRATOR_INTEGRATION.md](docs/CTFD_ORCHESTRATOR_INTEGRATION.md)
- [docs/CTFD_CHALLENGE_SYNC.md](docs/CTFD_CHALLENGE_SYNC.md)
- [docs/KUBERNETES_EXTENSION.md](docs/KUBERNETES_EXTENSION.md)

## Repository Strategy

This project now follows a single-repository model:

1. `main` is the production-ready reference branch.
2. Feature branches are merged by PR into `main`.
3. No upstream template synchronization is required.

### Key Feature Documentation

**Orchestrator API (New in v2.0):**
- Authentication: Token-based (`X-Orchestrator-Token`) for GET, HMAC-SHA256 signatures for POST
- Endpoints: `/status`, `/start`, `/stop`, `/cleanup`, `/ctfd/event` (webhook trigger)
- Security: Per-team rate limiting (30 req/min) + per-client (60 req/min), instance quotas (max 3 active)
- Audit: All events logged as JSON lines with timestamp, client IP, team, challenge, HTTP status

**Player Access Rendering (Current):**
- Challenges with spawnable runtime (`docker-compose.yml`) are orchestrated
- Static challenges are excluded from launch orchestration
- Launch page renders the right access mode:
	- `web`: browser button + optional auto-redirect
	- `ssh`: copy-ready commands for Linux/macOS and Windows PowerShell
	- `instruction`: textual instructions when no direct web endpoint applies

**Vault Integration (New in v2.0):**
- **Development:** Defaults in `ansible/vars/main.yml`, vault optional
- **Production:** Encrypted `ansible/vars/vault.yml` overrides all secrets via `*_effective` variables
- **CI/CD:** Vault password via GitHub Secrets or GitLab CI Variables, passed at runtime

**Challenges (Updated):**
- New warmup challenge: `challenges/web/simple-login/` for testing orchestrator deployment
- New SSH/VM example: `challenges/sandbox/ssh-lab/` with explicit SSH access rendering
- New instruction-only OSINT example: `challenges/osint/template-example/`
- Support for arbitrary Docker Compose services (not limited to specific languages)
- Per-team isolation via orchestrator port mapping

### Quick Reference: Access Points

After `vagrant up --provision`:

| Service | URL | Port | Purpose |
|---------|-----|------|---------|
| **CTFd** | http://192.168.56.10 | 8000 (internal) | Main CTF platform |
| **CTFd (Local)** | http://localhost:8000 | Forwarded | CTFd from host |
| **Orchestrator API** | http://192.168.56.10:8181 | 8181 (proxied) | Challenge instance control |
| **Orchestrator UI** | http://192.168.56.10:8181/ui | 8181 | Web dashboard |
