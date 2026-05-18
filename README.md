# CTF Platform Custom

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Vagrant](https://img.shields.io/badge/Vagrant-2.4%2B-blue)](https://www.vagrantup.com/)
[![Ansible](https://img.shields.io/badge/Ansible-2.14%2B-red)](https://www.ansible.com/)

## Overview

Single-repository platform for running a fully automated CTF with per-team Docker instances, custom dashboard, and challenge sync.

**Capabilities:**

- **Infrastructure** — Reproducible VM via Vagrant + Ansible, fully re-provisionable
- **Platform** — CTFd on Docker Compose with automated challenge sync
- **Challenges** — 32 challenges across 7 categories (crypto, forensics, linux, osint, reverse, sandbox, web), all with writeups in `/soluce`
- **Orchestration** — Per-team Docker instances, TTL-based cleanup, SSH/web launch pages
- **Static serving** — Forensics files and reverse binaries served directly via nginx at `/files/<category>/<name>/` — no instance required
- **Dashboard** — Custom CTFd plugin with instance cards, live activity, quick launch
- **Security** — HMAC-SHA256 signing, per-team rate limiting, instance quotas, Ansible Vault
- **Monitoring** — Prometheus + Grafana + cAdvisor (Grafana: anonymous Viewer access enabled)

---

## Quick Start

### Prerequisites

- [VirtualBox](https://www.virtualbox.org/wiki/Downloads) 7.0+
- [Vagrant](https://www.vagrantup.com/downloads) 2.4+
- 8 GB RAM and 4 CPU cores available for the VM
- ~20 GB free disk space (VM image + Docker images)

---

### First boot (dev / local)

```bash
git clone https://github.com/Z3nT1x777/ctfd-platform-iaac.git
cd ctfd-platform-iaac
vagrant up
```

No vault setup needed for local dev — `vagrant up` automatically creates `ansible/vars/vault.yml` from the example file with safe dev defaults. The playbook will print a warning listing secrets still at default values; this is expected.

`vagrant up` runs the full Ansible playbook automatically:
- Starts CTFd, MariaDB, Redis, Prometheus, Grafana
- Starts `player-instance-api` systemd service (orchestrator)
- Configures nginx reverse proxy
- Pre-builds all challenge Docker images
- Creates the `container-escape` flag on the host
- Syncs all challenges to CTFd (if `ctfd_api_token` is set in vault.yml)

Access points after provisioning:

| Service | URL |
|---------|-----|
| CTFd | http://192.168.56.10 |
| Orchestrator Dashboard | http://192.168.56.10/plugins/orchestrator/dashboard |
| Orchestrator Admin | http://192.168.56.10/plugins/orchestrator/admin |
| Orchestrator API | http://192.168.56.10:8181 |
| Grafana | http://192.168.56.10:3000 (anonymous Viewer) |
| OSINT static challenges | http://192.168.56.10/osint/\<challenge\>/resources/ |
| Forensics / Reverse files | http://192.168.56.10/files/\<category\>/\<challenge\>/\<file\> |

---

### One-time CTFd setup (required on first boot)

1. Open http://192.168.56.10 → complete the CTFd setup wizard (admin account + CTF name)
2. In CTFd: **Admin → Settings → Access Tokens → Generate** — copy the token
3. Add it to `ansible/vars/vault.yml` on your host machine:
   ```yaml
   ctfd_api_token: "your-token-here"
   ```
4. Re-run the playbook to sync challenges:
   ```bash
   vagrant provision
   ```

After this, every subsequent `vagrant up` or `vagrant provision` will sync challenges automatically.

> **Important:** `ORCHESTRATOR_PUBLIC_URL` (set to `http://192.168.56.10` in `ansible/vars/main.yml`) controls the base URL injected into CTFd challenge launch links. If you change the VM IP, update this variable and re-provision.

---

### Re-provisioning an existing VM

```bash
# Full re-provision (same as first boot)
vagrant provision

# Or via Ansible directly (faster, skips VM setup)
# Note: Ansible runs from /root/ctf-ansible/ inside the VM (copied from /vagrant/ansible/)
vagrant ssh -c "sudo bash -c 'cp -a /vagrant/ansible/. /root/ctf-ansible/ && cd /root/ctf-ansible && ansible-playbook -i inventory playbooks/main.yml'"

# With encrypted vault (production):
vagrant ssh -c "sudo bash -c 'cp -a /vagrant/ansible/. /root/ctf-ansible/ && cd /root/ctf-ansible && ansible-playbook -i inventory playbooks/main.yml --vault-password-file .vault_pass'"
```

---

## Secrets Setup

### Dev / local (fresh clone)

On a fresh `git clone`, `ansible/vars/vault.yml` does not exist (it is gitignored).
`vagrant up` automatically creates it from `vault.example.yml` so the platform starts with safe dev defaults — no manual step required.

The playbook will print a warning listing which secrets are still at their default values. This is expected for a local dev environment.

### Production

Before running `vagrant up`, create and fill `ansible/vars/vault.yml` with real credentials:

```bash
cp ansible/vars/vault.example.yml ansible/vars/vault.yml
```

Generate strong secrets and paste them into the file:

```bash
openssl rand -hex 32   # run once per secret — 64-char hex string
```

Edit `ansible/vars/vault.yml`:

```yaml
DB_ROOT_PASSWORD: "<generated>"
DB_PASSWORD: "<generated>"
orchestrator_api_token: "<generated>"
orchestrator_signing_secret: "<generated>"
orchestrator_ctfd_webhook_token: "<generated>"
grafana_admin_password: "<strong-password>"
ctfd_api_token: ""   # fill after first CTFd setup (see Quick Start)
```

Then encrypt and store the vault password (recommended):

```bash
ansible-vault encrypt ansible/vars/vault.yml
# Store the passphrase in ansible/.vault_pass (gitignored — never commit this file)
echo "your-passphrase" > ansible/.vault_pass
chmod 600 ansible/.vault_pass
```

`vagrant up` automatically detects `ansible/.vault_pass` and decrypts the vault — no extra flag needed. The `vault.yml` (encrypted or plain) is picked up via the shared folder.

> **Note on `DB_PASSWORD`:** if you change this after the first provision, delete `/opt/ctf/ctfd/db_data/` inside the VM before re-provisioning so MariaDB reinitialises with the new password.

> **First boot only:** complete the CTFd setup wizard, generate an API token (Admin → Settings → Access Tokens), add it to `ansible/vars/vault.yml` as `ctfd_api_token`, then run `vagrant provision` to sync challenges.

---

## Challenge Sync

Challenges are synced to CTFd via the API using `sync_challenges_ctfd.py`.

**Automatic** (runs at end of every Ansible playbook if `ctfd_api_token` is set):
- Creates/updates all challenges from `challenge.yml` files
- Sets flags, descriptions, hints, point values
- Links Docker challenges to the orchestrator launch page

**Manual sync** (useful during development):
```bash
vagrant ssh -c "python3 /vagrant/scripts/sync_challenges_ctfd.py \
  --ctfd-url http://127.0.0.1:8900 \
  --api-token YOUR_TOKEN \
  --challenges-root /vagrant/challenges \
  --instance-base-url http://192.168.56.10 \
  --connection-mode launch-link"
```

---

## Challenge Authoring

### Create a new challenge

```bash
# Linux/macOS
bash ./scripts/new-challenge.sh my-challenge --family linux

# Windows
./scripts/new-challenge.ps1 -Name my-challenge -Family linux
```

Each challenge needs at minimum:
```
challenges/<category>/<name>/
  Dockerfile          # Ubuntu base + vulnerability setup
  docker-compose.yml  # port mapping + image: ctf-<category>-<name>:latest
  challenge.yml       # name, category, value, flag, hints
```

### The image: field is required

Every `docker-compose.yml` must have an explicit `image:` tag:

```yaml
services:
  my-challenge:
    build: .
    image: ctf-linux-my-challenge:latest   # required for pre-build caching
    ports:
      - "5030:22"
    restart: unless-stopped
```

This allows the Ansible playbook to pre-build the image once at deploy time.
When a player launches the challenge, the orchestrator reuses the cached image — **launch is instant**.

### Start a challenge container manually (dev/test)

```bash
vagrant ssh -c "cd /vagrant/challenges/linux/01-suid-classic && docker compose up --build -d"
ssh player@192.168.56.10 -p 5020   # password: player2026
```

### Writeups

All challenge writeups live in `/soluce/<category>/<challenge>/README.md`.
These are for organizers and post-CTF disclosure — never exposed to players.

---

## Challenge Overview

| Category | Count | Type | Access |
|----------|-------|------|--------|
| crypto | 6 | static | instructions in CTFd |
| forensics | 6 | static | download via `/files/forensics/<name>/` |
| linux | 6 | docker | SSH per-team instance |
| osint | 2 | static | `/osint/<name>/resources/` |
| reverse | 4 | 2 static + 2 docker→static | download via `/files/reverse/<name>/` |
| sandbox | 2 | docker | SSH per-team instance |
| web | 6 | docker | per-team web instance |

Writeups for all challenges: `/soluce/<category>/<challenge>/README.md`

---

## Operations Commands

```bash
# Check all running containers
vagrant ssh -c "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Restart CTFd (after plugin changes)
vagrant ssh -c "docker restart ctfd"

# Restart orchestrator API
vagrant ssh -c "sudo systemctl restart player-instance-api.service"

# Check orchestrator API logs
vagrant ssh -c "sudo journalctl -u player-instance-api.service -n 50"

# Reload nginx (after config changes)
vagrant ssh -c "sudo nginx -t && sudo systemctl reload nginx"

# Pre-build a specific challenge image
vagrant ssh -c "cd /vagrant/challenges/linux/01-suid-classic && docker compose build"
```

---

## Repository Structure

```
.
├── ansible/
│   ├── playbooks/main.yml          # Full deploy playbook
│   ├── templates/                  # Jinja2 templates (nginx, docker-compose, systemd)
│   └── vars/
│       ├── main.yml                # Default config values
│       ├── vault.yml               # Secrets (gitignored, create from vault.example.yml)
│       └── vault.example.yml       # Template for vault.yml
├── challenges/
│   ├── crypto/                     # 6 static crypto challenges (01-06)
│   ├── forensics/                  # 6 forensics challenges — static file downloads
│   ├── linux/                      # 6 Linux privesc series (01-06, SSH)
│   ├── osint/                      # 2 OSINT challenges (static nginx)
│   ├── reverse/                    # 4 reverse challenges (2 static + 2 file downloads)
│   ├── sandbox/                    # 2 sandbox challenges (SSH)
│   ├── web/                        # 6 web challenges (per-team Docker)
│   └── _templates/                 # Challenge authoring templates
├── scripts/
│   ├── player-instance-api.py      # Orchestrator HTTP API (systemd service)
│   ├── player-instance-manager.sh  # Docker lifecycle manager (start/stop/extend/status)
│   ├── sync_challenges_ctfd.py     # Challenge sync script (CTFd API)
│   ├── sync_osint_static.py        # OSINT static file sync
│   └── ctfd-orchestrator-plugin/   # CTFd plugin (dashboard, launch pages, API endpoints)
├── soluce/                         # Writeups for all challenge categories
├── docs/                           # Extended documentation
└── README.md                       # This file
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md) | Challenge authoring, templates, validation |
| [docs/PLAYER_INSTANCE_ORCHESTRATOR.md](docs/PLAYER_INSTANCE_ORCHESTRATOR.md) | Orchestrator API reference |
| [docs/VAULT_SETUP.md](docs/VAULT_SETUP.md) | Ansible Vault setup for production |
| [docs/SECURITY_BASELINE.md](docs/SECURITY_BASELINE.md) | Security model and threat mapping |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [docs/MONITORING.md](docs/MONITORING.md) | Prometheus + Grafana setup |
| [docs/WORKFLOW_PRIORITIES.md](docs/WORKFLOW_PRIORITIES.md) | Dev workflow cheatsheet |
