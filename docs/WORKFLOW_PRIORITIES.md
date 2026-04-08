# Project Workflow & Priorities

## Overview

This document outlines the core project objectives, organized by priority level (P0-P3). Each level builds on the previous; higher priority items are prerequisites for lower priority items.

---

## P0: Infrastructure Stability

**Goal:** Reproducible `vagrant up` that works for all team members without manual intervention.

**Status:** ✅ **COMPLETE**

### Verification

```bash
# Provision from scratch
vagrant up --provision
vagrant status  # Should show "running"

# Check services
vagrant ssh -c "docker ps"
vagrant ssh -c "curl -I http://localhost:80"
vagrant ssh -c "sudo systemctl status ctf-orchestrator-api.service"
```

### Expected state

- VM in `running` state
- Docker containers active: `ctfd`, `postgres`, `redis`
- CTFd responds with 302 (redirect to setup) or 200 (if setup complete)
- Orchestrator API responds (requires token)
- nginx proxy operational on port 8181

### Critical infrastructure

- `Vagrantfile` - VM configuration, port forwarding, provisioning
- `ansible/playbooks/main.yml` - Ansible provisioning playbook
- `ansible/vars/main.yml` - Default configuration values
- `docker-compose-ctfd.yml.j2` - CTFd service stack template

---

## P1: Challenge Authoring Workflow

**Goal:** Create challenges in < 10 minutes without structure errors, with validation-first approach.

**Status:** ✅ **COMPLETE**

### Workflow

**Step 1: Generate from template**

```powershell
# Windows PowerShell
./scripts/new-challenge.ps1 -Name web-01-sqli -Family web
```

```bash
# Linux / macOS
bash ./scripts/new-challenge.sh web-01-sqli --family web
```

Creates: `challenges/web/web-01-sqli/` with skeleton files.

**Step 2: Customize challenge**

- Edit `app.py` - implement challenge logic
- Update `challenge.yml` - metadata, points, description
- Modify `requirements.txt` - dependencies
- Set `FLAG` in `flag.txt` and/or as environment variable
- Update `docker-compose.yml` if needed

**Step 3: Validate locally**

```powershell
# Windows PowerShell
./scripts/validate-challenge.ps1 -Path challenges/web/web-01-sqli
```

```bash
# Linux / macOS
bash ./scripts/validate-challenge.sh challenges/web/web-01-sqli
```

Validation checks:
- ✅ Required files present (Dockerfile, docker-compose.yml, challenge.yml, etc.)
- ✅ Valid YAML/JSON syntax
- ✅ No hardcoded development secrets
- ✅ Port mappings unique and non-conflicting
- ✅ Docker image builds without errors

**Step 4: Test in VM**

```bash
vagrant ssh -c "cd /vagrant/challenges/web/web-01-sqli && docker compose up -d --build"
curl http://192.168.56.10:<PORT>
vagrant ssh -c "cd /vagrant/challenges/web/web-01-sqli && docker compose down"
```

Or via orchestrator API:
```bash
# Start isolated instance
curl -X POST http://192.168.56.10:8181/start \
  -H "X-Orchestrator-Token: ..." \
  -H "X-Signature-Timestamp: $(date +%s)" \
  -H "X-Signature: ..." \
  -d '{"challenge": "web-01-sqli", "team_id": "1"}'
```

**Step 5: Commit and submit PR**

```bash
git checkout -b feat/challenge-web-01-sqli
git add challenges/web/web-01-sqli/
git commit -m "feat(challenge): add web-01-sqli (20 points, docker)"
git push -u origin feat/challenge-web-01-sqli
```

PR description should include:
- Brief description of challenge goal
- Difficulty / points
- Port(s) used
- Any special setup needed

### Templates

Available challenge families in `challenges/_templates/`:

| Family | Type | Docker | Use Case |
|--------|------|--------|----------|
| `web` | Docker | ✓ | Web apps, APIs, forms, injection |
| `osint` | Static | ✗ | Open source intelligence, documents |
| `sandbox` | Docker | ✓ | Isolated environments, VMs, system |
| `reverse` | Docker | ✓ | Reverse engineering, binary analysis |
| `pwn` | Docker | ✓ | Exploitation, memory corruption |

### Testing Example Challenge

A simple login challenge is included for testing: `challenges/web/simple-login/`

```bash
# Test via orchestrator
ts=$(date +%s); body='{"challenge":"simple-login","team_id":"1","ttl_min":60}'; \
sig=$(printf "%s.%s" "$ts" "$body" | openssl dgst -sha256 -hmac "ChangeMe-Orchestrator-Signing-Secret" -binary | xxd -p -c 256); \
curl -X POST http://192.168.56.10:8181/start \
  -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" \
  -H "X-Signature-Timestamp: $ts" \
  -H "X-Signature: $sig" \
  -d "$body"
```

---

## P2: Version Control & PR Workflow

**Goal:** Clean git history, avoid conflicts, maintain code quality standards.

**Status:** ✅ **COMPLETE**

### Git Workflow

**Branch naming conventions:**

```
feat/<feature-name>       # New features
fix/<bug-name>            # Bug fixes
docs/<doc-topic>          # Documentation  
refactor/<component>      # Code refactoring
test/<what-tested>        # Test additions
chore/<maintenance>       # Maintenance tasks
security/<hardening>      # Security improvements
```

**Standard PR workflow:**

```bash
# 1. Sync main
git checkout main
git pull --rebase origin main

# 2. Create feature branch
git checkout -b feat/my-feature

# 3. Make changes
# ...edit files...

# 4. Commit with clear messages
git add <files>
git commit -m "feat(component): description of change

- Additional detail about implementation
- Related issue: #123"

# 5. Push branch
git push -u origin feat/my-feature

# 6. Create PR on GitHub
# (link in PR template, reference issue, add description)
```

**PR Checklist:**

- [ ] Branch name follows convention (`feat/`, `fix/`, etc.)
- [ ] Commits have clear, descriptive messages
- [ ] All changes validated locally (scripts pass, builds work)
- [ ] No merge conflicts with `main`
- [ ] PR description explains what/why/how
- [ ] Related issues linked (#123)
- [ ] For challenges: metadata and structure validated
- [ ] For docs: links are correct, formatting clean
- [ ] For security changes: preflight checks pass

**Protected Branch Rules (main):**

- Require PR review (1 approval)
- Require status checks pass (CI workflows)
- Require branches up to date before merge
- Dismiss stale reviews on new commits

---

## P3: Security Hardening

**Goal:** Production-grade security architecture meeting M2 compliance standards.

**Status:** ✅ **FULLY IMPLEMENTED** (as of v2.0)

### Implemented Controls

All the following features are deployed and active. See [docs/SECURITY_BASELINE.md](SECURITY_BASELINE.md) for detailed explanations.

#### 1. API Token Authentication ✅
- Every endpoint requires `X-Orchestrator-Token` header
- Development default: `ChangeMe-Orchestrator-Token`
- Production: Override via Ansible Vault

#### 2. HMAC-SHA256 Request Signing ✅
- POST operations require cryptographic signatures
- Headers: `X-Signature-Timestamp`, `X-Signature`
- Prevents tampering and replay attacks
- 300-second timestamp validation

#### 3. Per-Client Rate Limiting ✅
- 60 requests/minute per IP address
- Uses X-Forwarded-For header tracking
- Configurable via `ORCHESTRATOR_RATE_LIMIT_PER_MIN`

#### 4. Per-Team Rate Limiting ✅
- 30 requests/minute per team_id
- Independent of per-client limit
- Configurable via `ORCHESTRATOR_TEAM_RATE_LIMIT_PER_MIN`

#### 5. Team Instance Quotas ✅
- Maximum 3 concurrent instances per team (configurable)
- Enforced on `/start` endpoint
- Returns 409 when quota exceeded

#### 6. Centralized Audit Logging ✅
- All events logged as JSON lines to `/var/log/ctf/orchestrator-audit.log`
- Includes: timestamp, event type, client IP, team, challenge, HTTP status
- Enables forensics and compliance audits

#### 7. CTFd Webhook Integration ✅
- `POST /ctfd/event` endpoint for CTFd integration
- Maps CTFd events to orchestrator actions
- Supports challenge.start, challenge.stop, cleanup events
- Same authentication (token + signature) required

#### 8. Localhost-Only API Binding ✅
- API binds to 127.0.0.1:18181 (internal only)
- nginx reverse proxy on 0.0.0.0:8181 (external)
- Defense in depth architecture

#### 9. Ansible Vault Secret Management ✅
- Encrypted `ansible/vars/vault.yml` overrides defaults
- Supports all secrets: DB passwords, API keys, webhook tokens
- Optional in development, required in production
- CI/CD integration via GitHub Secrets or GitLab CI Variables

#### 10. Security Preflight CI Workflow ✅
- Detects development defaults in pull requests
- Warns on `ChangeMe-*`, `demo-*`, weak credentials
- Strict mode (`SECURITY_STRICT=1`) fails pipeline if issues found
- Runs on all PRs targeting protected branches

### Operational Requirements

#### Development (Optional Vault)

```bash
# Just use defaults, no vault needed
vagrant up --provision
```

#### Production (Vault Required)

```bash
# 1. Create vault file
cp ansible/vars/vault.example.yml ansible/vars/vault.yml

# 2. Encrypt with Ansible Vault
ansible-vault encrypt ansible/vars/vault.yml

# 3. Edit with secure values  
ansible-vault edit ansible/vars/vault.yml

# 4. Provide vault password at provision time
ansible-playbook playbooks/main.yml --vault-password-file=/path/to/vault-pass.txt
```

### Configuration Defaults

All values in `ansible/vars/main.yml` (can be overridden via `vault.yml`):

```yaml
# API Authentication
orchestrator_token: ChangeMe-Orchestrator-Token
orchestrator_signing_secret: ChangeMe-Orchestrator-Signing-Secret
orchestrator_ctfd_webhook_token: ChangeMe-CTFd-Webhook-Token

# Rate Limiting
orchestrator_rate_limit_per_min: 60          # Per-client
orchestrator_team_rate_limit_per_min: 30     # Per-team

# Quotas
orchestrator_team_max_active: 3              # Max instances per team

# Security
orchestrator_signature_ttl_sec: 300          # HMAC timestamp TTL
orchestrator_audit_log: /var/log/ctf/orchestrator-audit.log

# Binding (changed in v2.0 - now localhost-only)
orchestrator_api_host: 127.0.0.1
orchestrator_api_port: 18181
```

### Testing Security Features

```bash
# 1. Test authentication
curl -i http://192.168.56.10:8181/status  # 401 Unauthorized
curl -i -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" \
  http://192.168.56.10:8181/status  # 200 OK

# 2. Test signature requirement
curl -i -X POST -H "X-Orchestrator-Token: ..." \
  http://192.168.56.10:8181/start  # 401 Unauthorized (missing_signature_headers)

# 3. Check audit logs
vagrant ssh -- sudo tail /var/log/ctf/orchestrator-audit.log

# 4. Test rate limiting (make 61 requests)
for i in {1..61}; do
  curl -s -H "X-Orchestrator-Token: ..." \
    http://192.168.56.10:8181/status
done
# Last request should return 429 Too Many Requests

# 5. Test team quota
ts=$(date +%s); for i in {1..4}; do
  body="{\"challenge\":\"web-01\",\"team_id\":\"1\"}"; \
  sig=$(printf "%s.%s" "$ts" "$body" | openssl dgst -sha256 -hmac "..." -binary | xxd -p -c 256); \
  curl -X POST http://192.168.56.10:8181/start \
    -H "X-Orchestrator-Token: ..." \
    -H "X-Signature-Timestamp: $ts" \
    -H "X-Signature: $sig" \
    -d "$body"
done
# First 3: 200 OK; 4th: 409 Conflict
```

---

## Current Status Summary

| Priority | Objective | Status | Evidence |
|----------|-----------|--------|----------|
| **P0** | Infrastructure stability | ✅ COMPLETE | `vagrant up` provisions all services reliably |
| **P1** | Challenge authoring workflow | ✅ COMPLETE | Templates, validation scripts, example challenges |
| **P2** | Git / PR workflow | ✅ COMPLETE | Protected main branch, PR rules, CI/CD |
| **P3** | Security hardening | ✅ COMPLETE | All 10 controls implemented, tested, documented |

---

## Next Steps Beyond P3

Possible future enhancements (not yet prioritized):

- **Multi-team tournaments:** Scoreboard, live leaderboards, team submissions
- **Challenge auto-generation:** Create challenges from code templates
- **Advanced analytics:** Challenge difficulty metrics, time-to-solve distributions
- **Discord/Slack integration:** Real-time notifications on challenge completions
- **Kubernetes deployment:** Scale from VirtualBox to cloud (AWS, Azure, GCP)
- **Advanced monitoring:** Prometheus/Grafana for infrastructure metrics
- **SAML/LDAP auth:** Enterprise user directory integration
- **Backup/restore:** Automated challenge instance snapshots

---

## Documentation References

- [docs/README_CHALLENGES.md](README_CHALLENGES.md) - Challenge authoring guide
- [docs/PLAYER_INSTANCE_ORCHESTRATOR.md](PLAYER_INSTANCE_ORCHESTRATOR.md) - Orchestrator API reference
- [docs/SECURITY_BASELINE.md](SECURITY_BASELINE.md) - Security controls deep-dive
- [docs/VAULT_SETUP.md](VAULT_SETUP.md) - Ansible Vault configuration
- [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Debugging & operations
- [README.md](../README.md) - Project overview
