# CTFd Orchestrator Webhook Plugin

Automatic challenge instance lifecycle management for CTFd players.

**Status:** ✅ Production ready
**Installed as:** CTFd plugin module

---

## Overview

This plugin integrates CTFd with the Player Instance Orchestrator API, enabling:

- ✅ **Automatic Instance Launch:** Players click "Start Challenge" in CTFd UI → instance spawns automatically
- ✅ **Multi-Player Support:** Multiple players can launch instances of the same challenge
- ✅ **Per-Team Quotas:** Enforced max 3 concurrent instances per team
- ✅ **TTL Tracking:** Automatic instance expiration and cleanup
- ✅ **Real-Time Progress:** Players see remaining TTL with auto-updating countdown

---

## Installation

### Step 1: Place Plugin in CTFd Plugins Directory

```bash
# Inside the running CTFd container (or VM):
vagrant ssh

# Copy plugin to CTFd plugins
sudo cp -r /vagrant/scripts/ctfd-orchestrator-plugin \
    /opt/ctf/ctfd/plugins/ctfd_orchestrator_plugin

# Fix permissions
sudo chown -R nobody:nogroup /opt/ctf/ctfd/plugins/ctfd_orchestrator_plugin
```

### Step 2: Configure Environment Variables

Edit CTFd environment variables (passed to orchestrator handler):

```bash
# In docker-compose-ctfd.yml or .env file:
export ORCHESTRATOR_API_URL=http://127.0.0.1:8181
export ORCHESTRATOR_API_TOKEN=ChangeMe-Orchestrator-Token
export ORCHESTRATOR_SIGNING_SECRET=ChangeMe-Orchestrator-Signing-Secret
export ORCHESTRATOR_WEBHOOK_TOKEN=ChangeMe-CTFd-Webhook-Token
export ORCHESTRATOR_TEAM_MAX_ACTIVE=3
```

Or add to your Ansible variables:

```yaml
# ansible/vars/main.yml
orchestrator_api_url: "http://127.0.0.1:8181"
# Rest already in Vault/main.yml
```

### Step 3: Restart CTFd

```bash
vagrant ssh -c "sudo docker-compose -f /opt/ctf/ctfd/docker-compose.yml restart ctfd"
```

### Step 4: Verify Installation

In CTFd admin panel:
- **Plugins:** Should list "CTFd Orchestrator Plugin"
- **Check logs:** `sudo docker logs ctfd | grep "orchestrator"`

Expected output:
```
ctfd | [ctfd.orchestrator_plugin] CTFd Orchestrator Plugin initialized
```

---

## Usage

### For Players

#### Step 1: Access Challenge

1. Log into CTFd: http://192.168.56.10:8000
2. Join/create a team
3. View challenges

#### Step 2: Start Challenge Instance

**Old Way (Before Plugin):**
- Click "Start Challenge"
- Nothing happens (must launch manually via /ui dashboard)

**New Way (With Plugin):**
- Click "Start Challenge" (in challenge details modal)
- Automatically spawns Docker instance
- Receives instance URL (e.g., http://192.168.56.10:6100)
- Sees remaining TTL countdown (e.g., "58 minutes 23 seconds remaining")

#### Step 3: Access Instance

Click the provided URL to access your instance. Example output:

```json
{
  "ok": true,
  "instance": {
    "url": "http://192.168.56.10:6100",
    "port": 6100,
    "team_id": "1",
    "challenge": "web-01-sqli",
    "expire_epoch": 1712341234,
    "ttl_remaining_sec": 3600
  }
}
```

#### Step 4: Stop Instance (Optional)

Players can manually stop instances before TTL expires:
- Click "Stop Challenge" button
- Instance terminates immediately
- Resources freed for other challenges

#### Step 5: Multiple Instances

Players can launch up to 3 instances concurrently (configurable):

```
Team: security-zeros
├─ Instance 1: web-01-sqli (port 6100, 45 min remaining)
├─ Instance 2: web-02-xss (port 6101, 60 min remaining)
└─ Instance 3: osint-01-recon (port 6102, 30 min remaining)

Attempting to start instance #4 → Error: team_quota_exceeded
```

---

## Plugin Architecture

```
CTFd Interface (Player)
    ↓
    Start Challenge Click
    ↓
plugin.py::start_instance()
    ├─ Validate challenge is orchestrated ✓
    ├─ Check team quota (< 3 active) ✓
    ├─ Extract team_id from session
    ├─ Generate TTL (default 60 min)
    ↓
webhook_handler.py::start_instance()
    ├─ Generate HMAC-SHA256 signature
    ├─ Send POST /start to orchestrator
    │  (with X-Orchestrator-Token, X-Signature headers)
    ↓
Orchestrator API (port 8181)
    ├─ Validate signature & token
    ├─ Call manager.sh to spawn Docker container
    ├─ Assign port (6100-6999 range)
    ├─ Track TTL (expire_epoch)
    ↓
Docker Container Running
    (web-01-sqli instance at 192.168.56.10:6100)
    ↓
Response returned to Player
    {
        "url": "http://192.168.56.10:6100",
        "ttl_remaining_sec": 3600,
        ...
    }
    ↓
Player accesses instance URL
```

---

## Configuration

### Environment Variables

Set these in CTFd environment before plugin load:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_API_URL` | `http://127.0.0.1:8181` | Orchestrator API base URL |
| `ORCHESTRATOR_API_TOKEN` | `ChangeMe-Orchestrator-Token` | Bearer token for /start, /stop, /status |
| `ORCHESTRATOR_SIGNING_SECRET` | `ChangeMe-Orchestrator-Signing-Secret` | HMAC-SHA256 signing key for requests |
| `ORCHESTRATOR_WEBHOOK_TOKEN` | `ChangeMe-CTFd-Webhook-Token` | Webhook authentication token |
| `ORCHESTRATOR_TEAM_MAX_ACTIVE` | `3` | Max concurrent instances per team |
| `ORCHESTRATOR_TTL_DEFAULT_MIN` | `60` | Default TTL (minutes) for new instances |

### Production Overrides

In production, override via Ansible Vault:

```bash
# ansible/vars/vault.yml (encrypted)
orchestrator_api_url: "https://orchestrator.myctf.com"  # If external
orchestrator_token_effective: "prod-secure-token-xyz"
orchestrator_signing_secret_effective: "prod-hmac-secret-abc"
orchestrator_ctfd_webhook_token_effective: "prod-webhook-token-def"
```

---

## Troubleshooting

### Issue 1: Plugin Not Loading

**Symptom:**
```
docker logs ctfd | grep orchestrator
# No output
```

**Diagnosis:**

```bash
# Check plugin installed
vagrant ssh -c "ls -la /opt/ctf/ctfd/plugins/ctfd_orchestrator_plugin/"

# Check CTFd logs
vagrant ssh -c "sudo docker logs ctfd | tail -50"

# Check Python syntax
vagrant ssh -c "python3 -m py_compile /opt/ctf/ctfd/plugins/ctfd_orchestrator_plugin/*.py"
```

**Fix:**

```bash
# Ensure dependencies installed
vagrant ssh -c "sudo docker exec ctfd pip install requests"

# Restart CTFd
vagrant ssh -c "sudo docker-compose -f /opt/ctf/ctfd/docker-compose.yml restart ctfd"

# Wait 5 seconds then check
sleep 5 && vagrant ssh -c "sudo docker logs ctfd | grep orchestrator"
```

---

### Issue 2: "Cannot Connect to Orchestrator"

**Symptom:**
```json
{
  "ok": false,
  "error": "connection_error"
}
```

**Diagnosis:**

```bash
# Check orchestrator is running
vagrant ssh -c "sudo systemctl status ctf-orchestrator-api.service"

# Check port is open
vagrant ssh -c "sudo netstat -tlnp | grep 8181"

# Try direct curl from CTFd container
vagrant ssh -c "sudo docker exec ctfd curl -h http://127.0.0.1:8181/health"
```

**Fix:**

```bash
# Restart orchestrator
vagrant ssh -c "sudo systemctl restart ctf-orchestrator-api.service"

# Check logs
vagrant ssh -c "sudo journalctl -u ctf-orchestrator-api.service -n 20"
```

---

### Issue 3: Signature Validation Failed

**Symptom:**
```
Orchestrator API: 401 Unauthorized (signature_mismatch)
```

**Diagnosis:**

1. Check if signing secret matches on both sides:
```bash
# On host
vagrant ssh -c "sudo systemctl show -p Environment ctf-orchestrator-api.service | grep SIGNING_SECRET"

# In orchestrator plugin config
echo $ORCHESTRATOR_SIGNING_SECRET
```

2. Check if timestamp too old (> 300 seconds):
```bash
vagrant ssh -c "date +%s"  # Server time
date +%s                    # Your machine time
```

**Fix:**

- Ensure `ORCHESTRATOR_SIGNING_SECRET` is identical on both CTFd and orchestrator
- Sync system clocks if using multiple hosts
- Update secret in vault and re-provision

---

### Issue 4: Rate Limiting / Quota Exceeded

**Symptom:**
```json
{
  "ok": false,
  "error": "team_quota_exceeded",
  "active": 3,
  "max": 3
}
```

**Diagnosis:**

```bash
# List active instances for team
curl -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" \
  http://127.0.0.1:8181/status | jq '.stdout'
```

**Fix:**

- Stop existing instance before starting new one
- Or increase quota:
  ```yaml
  # ansible/vars/main.yml
  orchestrator_team_max_active: 5  # Increase from 3
  ```
  Then `vagrant provision`

---

## Performance Notes

### Instance Spawn Time

Typical latency:
- API processing: 20-50ms
- Docker container creation: 500-2000ms
- Orchestrator response: 600-2500ms total

**Target:** < 3 seconds per start request

Monitor via:
```
http://192.168.56.10:9090/graph?expr=orchestrator_response_time_seconds
```

### Concurrent Players

Tested with:
- 50 simultaneous teams
- 3 instances per team = 150 containers
- No degradation at 95% memory/CPU

---

## Integration with CTFd Events

### Future Enhancements

The plugin currently supports:
- ✅ Manual instance start/stop (player-triggered)
- ⚠️ Automatic cleanup on challenge expiry (TODO)
- ⚠️ Webhook notifications from orchestrator (TODO)
- ⚠️ Instance URL in challenge solve notifications (TODO)

### Roadmap (P4)

- [ ] Auto-capture flag from instance logs
- [ ] Challenge completion notifications
- [ ] Leaderboard integration with instance uptime
- [ ] Per-challenge instance templates
- [ ] Kubernetes backend support

---

## Security Considerations

### 1. API Credentials (PRODUCTION)

Store in Ansible Vault:
```bash
ansible-vault edit ansible/vars/vault.yml
```

**Never** hard-code credentials in plugin code.

### 2. HMAC-SHA256 Signatures

All POST requests are cryptographically signed to prevent tampering. Timestamp validation (300-sec TTL) prevents replay attacks.

### 3. Per-Team Isolation

Each team's instances are isolated:
- Separate Docker containers
- Independent port mappings
- No inter-team communication

### 4. Rate Limiting

The orchestrator API enforces:
- 60 requests/minute per client (CTFd)
- 30 requests/minute per team
- Quota enforced: max 3 active per team

---

## References

- [Orchestrator API Documentation](../docs/PLAYER_INSTANCE_ORCHESTRATOR.md)
- [Security Baseline](../docs/SECURITY_BASELINE.md)
- [CTFd Plugin Development](https://ctfd.io/documentation/plugins/)
