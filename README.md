# CTF Platform Infrastructure as Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Vagrant](https://img.shields.io/badge/Vagrant-2.4%2B-blue)](https://www.vagrantup.com/)
[![Ansible](https://img.shields.io/badge/Ansible-2.14%2B-red)](https://www.ansible.com/)

## Overview

This repository provides an end-to-end Infrastructure as Code setup for a self-hosted CTF platform.

Core capabilities already implemented:

- Reproducible VM provisioning with Vagrant and Ansible
- CTFd deployment on Docker Compose
- Challenge templates by family (`web`, `osint`, `sandbox`, `reverse`, `pwn`)
- Local and CI challenge structure validation
- Per-team challenge instance orchestration with TTL-based cleanup
- API authentication and rate limiting for orchestrator control
- Web UI for orchestrator operations
- Security preflight checks in CI

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

- Keep `.env` local and never commit it.
- Development defaults may still exist in `ansible/vars/main.yml` depending on environment.
- Run security preflight checks for pull requests touching sensitive configuration.
- For strict enforcement in CI or local checks:

```bash
SECURITY_STRICT=1 python scripts/security-preflight.py
```

## Documentation

- [docs/WORKFLOW_PRIORITES.md](docs/WORKFLOW_PRIORITES.md)
- [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md)
- [docs/PLAYER_INSTANCE_ORCHESTRATOR.md](docs/PLAYER_INSTANCE_ORCHESTRATOR.md)
- [docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md)
