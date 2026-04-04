# CTF Platform Infrastructure as Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Vagrant](https://img.shields.io/badge/Vagrant-2.4%2B-blue)](https://www.vagrantup.com/)
[![Ansible](https://img.shields.io/badge/Ansible-2.14%2B-red)](https://www.ansible.com/)

## Overview

This repository provides an end-to-end Infrastructure as Code setup for a self-hosted CTF platform.

Core capabilities already implemented:

- **Infrastructure:** Reproducible VM provisioning with Vagrant and Ansible
- **Platform:** CTFd deployment on Docker Compose with centralized configuration
- **Challenges:** Templates by family (`web`, `osint`, `sandbox`, `reverse`, `pwn`) with CI validation
- **Orchestration:** Per-team challenge instance management with automatic TTL-based cleanup
- **API Security:** HMAC-SHA256 request signing, per-team rate limiting (30 req/min), per-client rate limiting (60 req/min)
- **Quotas:** Per-team instance quotas (max 3 concurrent by default, configurable)
- **Audit Logging:** Centralized JSON audit logs to `/var/log/ctf/orchestrator-audit.log` with event tracking
- **webhooks**: CTFd event trigger endpoint (`POST /ctfd/event`) for automated instance lifecycle
- **Web UI:** Dashboard for orchestrator operations with team instance controls
- **Secrets Management:** Ansible Vault support for production secret overrides (passwords, API keys, signing secrets)
- **Reverse Proxy:** nginx ingress for controlled API exposure with X-Forwarded-For client tracking
- **Validation:** Security preflight checks in CI and git hooks

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
git clone https://github.com/USERNAME/ctf-platform-iaac.git
cd ctf-platform-iaac
vagrant up --provision
```

Access points after provisioning:

- CTFd: http://192.168.56.10
- CTFd (forwarded): http://localhost:8000
- Orchestrator UI: http://192.168.56.10:8181/ui

## Challenge Authoring Workflow

Use family templates from [challenges/_templates](challenges/_templates).

Windows example:

```powershell
./scripts/new-challenge.ps1 -Name web-01-test -Family web
./scripts/validate-challenge.ps1 -Path challenges/web-01-test
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

Linux/macOS example:

```bash
bash ./scripts/new-challenge.sh web-01-test --family web
bash ./scripts/validate-challenge.sh challenges/web-01-test
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

Detailed guide: [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md)

## Security Notes

### Overview: 10 Security Controls ✅

All the following security controls are implemented and active in production:

| Control | Implementation | Development | Production | Status |
|---------|----------------|-------------|------------|--------|
| **1. API Token Auth** | `X-Orchestrator-Token` header on all endpoints | `ChangeMe-Orchestrator-Token` | Override via Vault | ✅ |
| **2. HMAC-SHA256 Signatures** | POST operations require cryptographic signatures (timestamp + body) | `ChangeMe-Orchestrator-Signing-Secret` | Override via Vault | ✅ |
| **3. Per-Client Rate Limiting** | 60 requests/minute per IP address (X-Forwarded-For header) | Configurable | Env var: `ORCHESTRATOR_RATE_LIMIT_PER_MIN` | ✅ |
| **4. Per-Team Rate Limiting** | 30 requests/minute per team_id | Configurable | Env var: `ORCHESTRATOR_TEAM_RATE_LIMIT_PER_MIN` | ✅ |
| **5. Team Instance Quotas** | Max 3 concurrent instances per team (returns 409 when exceeded) | Configurable | Env var: `ORCHESTRATOR_TEAM_MAX_ACTIVE` | ✅ |
| **6. Audit Logging** | JSON centralized logging to `/var/log/ctf/orchestrator-audit.log` | All events tracked | Compliance-ready queries | ✅ |
| **7. CTFd Webhook** | `POST /ctfd/event` endpoint with `X-CTFd-Webhook-Token` validation | Webhook ready | Plugin integration TBD | ✅ API |
| **8. Localhost-Only Binding** | API binds to 127.0.0.1:18181 (internal only, nginx proxy external) | Defense in depth | nginx reverse proxy on 0.0.0.0:8181 | ✅ |
| **9. Ansible Vault** | Encrypted secret overrides for production credentials | Optional (defaults OK) | Required - all secrets in vault.yml | ✅ |
| **10. Security Preflight CI** | Detects development defaults in PRs, fails on ChangeMe-* warnings | GitHub Actions | Blocks merge if insecure defaults | ✅ |

### Setup for Development vs. Production

**Development (on your laptop):**
```bash
git clone https://github.com/USERNAME/ctf-platform-iaac.git
cd ctf-platform-iaac
vagrant up --provision
# Default credentials are safe for local VM testing
# No vault needed, all defaults from ansible/vars/main.yml
```

**Production (secure deployment):**
```bash
# 1. Create encrypted vault file
cp ansible/vars/vault.example.yml ansible/vars/vault.yml
ansible-vault encrypt ansible/vars/vault.yml

# 2. Edit with secure values
ansible-vault edit ansible/vars/vault.yml
# Override: orchestrator_token, orchestrator_signing_secret, DB passwords, etc.

# 3. Provision with vault password
ansible-playbook playbooks/main.yml --vault-password-file=/secure/path/vault-pass.txt

# 4. Run security preflight
SECURITY_STRICT=1 python scripts/security-preflight.py
```

**CI/CD Integration:**
```bash
# GitHub Actions / GitLab CI: Pass vault password via secrets
# Set ANSIBLE_VAULT_PASSWORD environment variable
# SeeI docs/VAULT_SETUP.md for complete CI/CD integration guide
```

### More Information

- **Detailed controls & threat mapping:** See [docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md)
- **Vault setup for production:** See [docs/VAULT_SETUP.md](docs/VAULT_SETUP.md)
- **Troubleshooting & debugging:** See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [docs/WORKFLOW_PRIORITES.md](docs/WORKFLOW_PRIORITES.md) | Project roadmap by priority level (P1-P3), current implementation status | Project leads, contributors |
| [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md) | Challenge authoring and deployment workflow, template structure, validation rules | CTF authors, challenge creators |
| [docs/PLAYER_INSTANCE_ORCHESTRATOR.md](docs/PLAYER_INSTANCE_ORCHESTRATOR.md) | Orchestrator API reference, endpoints, HMAC request signing, team quotas, audit logs | Developers, DevOps, API consumers |
| [docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md) | Security hardening controls, attack surface analysis, implemented defenses | Security engineers, auditors |
| [docs/VAULT_SETUP.md](docs/VAULT_SETUP.md) | Ansible Vault configuration for production secrets, CI/CD integration, best practices | DevOps, sysadmins, operators |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | nginx & orchestrator debugging, common issues, log locations, emergency procedures | Operators, DevOps engineers |
| [docs/MONITORING.md](docs/MONITORING.md) | Prometheus & Grafana setup, metrics collection, dashboard creation, production alerting | DevOps engineers, ops team |
| [docs/CTFD_ORCHESTRATOR_INTEGRATION.md](docs/CTFD_ORCHESTRATOR_INTEGRATION.md) | CTFd plugin for automatic instance launch, player workflow, multi-team quotas | CTF organizers, players, developers |
| [docs/CTFD_CHALLENGE_SYNC.md](docs/CTFD_CHALLENGE_SYNC.md) | Git to CTFd API sync for challenge create/update and flag upsert (GitOps publishing flow) | CTF admins, platform maintainers |
| [docs/KUBERNETES_EXTENSION.md](docs/KUBERNETES_EXTENSION.md) | Kubernetes extension path, migration model from Docker Compose to K8s, rollout strategy | Platform engineers, DevOps |

### Key Feature Documentation

**Orchestrator API (New in v2.0):**
- Authentication: Token-based (`X-Orchestrator-Token`) for GET, HMAC-SHA256 signatures for POST
- Endpoints: `/status`, `/start`, `/stop`, `/cleanup`, `/ctfd/event` (webhook trigger)
- Security: Per-team rate limiting (30 req/min) + per-client (60 req/min), instance quotas (max 3 active)
- Audit: All events logged as JSON lines with timestamp, client IP, team, challenge, HTTP status

**Vault Integration (New in v2.0):**
- **Development:** Defaults in `ansible/vars/main.yml`, vault optional
- **Production:** Encrypted `ansible/vars/vault.yml` overrides all secrets via `*_effective` variables
- **CI/CD:** Vault password via GitHub Secrets or GitLab CI Variables, passed at runtime

**Challenges (Updated):**
- New warmup challenge: `challenges/web/simple-login/` for testing orchestrator deployment
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
