# nginx & Orchestrator Troubleshooting Guide

## Architecture Overview

```
Client (outside VM)
    ├── :80  → nginx (ctfd.conf)
    │              ├── /osint/*  → /var/www/osint/  [static OSINT assets]
    │              └── /*        → CTFd (127.0.0.1:8900)
    └── :8181 → nginx (orchestrator-api.conf)
                   └── /*        → orchestrator API (127.0.0.1:18181)
                                     └── Manager subprocess [Docker runner]
```

Two nginx server blocks run on the VM:
- **Port 80** (`/etc/nginx/sites-enabled/ctfd.conf`): front-proxy for CTFd + static OSINT serving
- **Port 8181** (`/etc/nginx/sites-enabled/orchestrator-api.conf`): reverse proxy for the orchestrator API

CTFd binds to **localhost only** (127.0.0.1:8900); the orchestrator API binds to **localhost only** (127.0.0.1:18181).

---

## Quick Health Check

```bash
# 1. Check if both services are running
vagrant ssh -- sudo systemctl status ctf-orchestrator-api.service
vagrant ssh -- sudo systemctl status nginx

# 2. Check if ports are listening
vagrant ssh -- sudo ss -tlnp | grep -E ':(8181|18181)'

# 3. Quick API test
vagrant ssh -- curl -i http://127.0.0.1:18181/health
```

Expected output: Both services active, both ports listening, /health returns 200 OK.

---

## Operations Command Cookbook

These are high-value commands for day-to-day operations in the custom platform.

### Re-apply Ansible with a quota profile

Use one of these profiles to update orchestrator limits and service config:

```bash
# small teams
vagrant ssh -c "cd /vagrant/ansible && ansible-playbook -i inventory playbooks/main.yml -e orchestrator_quota_profile=small"

# medium teams
vagrant ssh -c "cd /vagrant/ansible && ansible-playbook -i inventory playbooks/main.yml -e orchestrator_quota_profile=medium"

# large teams
vagrant ssh -c "cd /vagrant/ansible && ansible-playbook -i inventory playbooks/main.yml -e orchestrator_quota_profile=large"
```

### Re-apply Ansible and restart API in one line

```bash
vagrant ssh -c "cd /vagrant/ansible && ansible-playbook -i inventory playbooks/main.yml -e orchestrator_quota_profile=small && sudo systemctl restart player-instance-api.service"
```

### Restart CTFd container only

```bash
vagrant ssh -c "docker restart ctfd"
```

### Restart full CTFd compose stack

```bash
vagrant ssh -c "cd /opt/ctf/ctfd && docker compose restart"
```

### Verify applied quota values

```bash
vagrant ssh -c "sudo cat /etc/ctf/orchestrator.env | grep -E 'ORCHESTRATOR_TEAM_(MAX_ACTIVE|CHALLENGE_MAX_ACTIVE|RATE_LIMIT_PER_MIN)'"
```

---

## Common Issues & Solutions

### Issue 1: "Connection refused" when testing API

**Symptoms:**
```
$ curl http://127.0.0.1:8181/status
curl: (7) Failed to connect to 127.0.0.1 port 8181: Connection refused
```

**Diagnosis:**

1. Check if nginx is running:
   ```bash
   vagrant ssh -- sudo systemctl status nginx
   ```

2. Check if orchestrator API is running:
   ```bash
   vagrant ssh -- sudo systemctl status ctf-orchestrator-api.service
   ```

3. Check listening ports:
   ```bash
   vagrant ssh -- sudo netstat -tlnp | grep -E 'nginx|python'
   ```

**Solutions:**

- **If nginx is down:**
  ```bash
  vagrant ssh -- sudo systemctl start nginx
  vagrant ssh -- sudo systemctl restart nginx  # Full restart
  ```

- **If orchestrator API is down:**
  ```bash
  vagrant ssh -- sudo systemctl start ctf-orchestrator-api.service
  vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service
  ```

- **If ports aren't listening, check logs:**
  ```bash
  # nginx error log
  vagrant ssh -- sudo tail -n 50 /var/log/nginx/error.log
  
  # orchestrator API log (systemd journal)
  vagrant ssh -- sudo journalctl -u ctf-orchestrator-api.service -n 50 --no-pager
  ```

---

### Issue 2: nginx Parse Error (Bad Gateway / Upstream Connect Failure)

**Symptoms:**
```
$ curl -i http://127.0.0.1:8181/status
HTTP/1.1 502 Bad Gateway
```

**Causes:**
- nginx config file has syntax error
- Upstream (orchestrator API) is not responding
- Upstream socket path is wrong

**Diagnosis:**

1. Test nginx config:
   ```bash
   vagrant ssh -- sudo nginx -t
   ```
   Expected: `nginx: configuration file OK`

2. Check if orchestrator is running on the right port:
   ```bash
   vagrant ssh -- sudo netstat -tlnp | grep 18181
   ```
   Expected: `tcp ... 127.0.0.1:18181 ... LISTEN`

3. Check nginx error log:
   ```bash
   vagrant ssh -- sudo tail -n 100 /var/log/nginx/error.log | grep -A5 "upstream"
   ```

**Solutions:**

- **If config test fails:**
  ```bash
  # Check both nginx configs
  cat /etc/nginx/sites-enabled/ctfd.conf           # port 80: CTFd proxy + /osint/
  cat /etc/nginx/sites-enabled/orchestrator-api.conf  # port 8181: orchestrator proxy
  ```

- **If orchestrator isn't responding:**
  ```bash
  # Restart orchestrator
  vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service
  
  # Wait 2 seconds
  sleep 2
  
  # Test again
  curl -i http://127.0.0.1:8181/status
  ```

- **If config is OK but still failing:**
  ```bash
  # Reload nginx without restarting (graceful)
  vagrant ssh -- sudo systemctl reload nginx
  ```

---

### Issue 3: "401 Unauthorized" or "Missing Token"

**Symptoms:**
```
$ curl http://127.0.0.1:8181/status
{"ok": false, "error": "unauthorized"}
```

**Expected behavior:** All GET/POST endpoints require authentication.

**Solutions:**

1. **For GET requests**, provide token header:
   ```bash
   curl -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" http://127.0.0.1:8181/status
   ```

2. **For POST requests**, provide token + HMAC signature:
   ```bash
   ts=$(date +%s)
   sig=$(printf "%s." "$ts" | openssl dgst -sha256 -hmac "ChangeMe-Orchestrator-Signing-Secret" -binary | xxd -p -c 256)
   curl -X POST \
     -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" \
     -H "X-Signature-Timestamp: $ts" \
     -H "X-Signature: $sig" \
     http://127.0.0.1:8181/cleanup
   ```

3. **Verify secrets are set correctly:**
   ```bash
   # Check environment variables
   vagrant ssh -- sudo systemctl show -p Environment ctf-orchestrator-api.service | grep -i orchestrator
   ```

---

### Issue 4: "Signature Invalid" on POST Requests

**Symptoms:**
```
{"ok": false, "error": "signature_invalid"}
```

**Causes:**
- Secret key mismatch (client using wrong signing secret)
- Timestamp too old (> 300 seconds)
- Malformed signature headers

**Diagnosis:**

1. Check if timestamp is recent:
   ```bash
   ts=$(date +%s); echo "Current: $ts"; curl -X POST \
     -H "X-Signature-Timestamp: $ts" \
     -H "X-Signature: test" \
     http://127.0.0.1:8181/cleanup 2>&1 | grep -o '"detail":"[^"]*"'
   ```

2. Verify signing secret in environment:
   ```bash
   vagrant ssh -- sudo systemctl show -p Environment ctf-orchestrator-api.service | grep SIGNING_SECRET
   ```

3. Manually test signature generation:
   ```bash
   ts=1234567890
   msg="${ts}."
   secret="ChangeMe-Orchestrator-Signing-Secret"
   sig=$(echo -n "$msg" | openssl dgst -sha256 -hmac "$secret" -binary | xxd -p -c 256)
   echo "Timestamp: $ts"
   echo "Signature: $sig"
   ```

**Solutions:**

- **If timestamp too old:**
  Use current timestamp:
  ```bash
  ts=$(date +%s)
  # Then generate signature with new timestamp
  ```

- **If secret mismatch:**
  Verify both client and server use same secret:
  ```bash
  # Server
  vagrant ssh -- sudo systemctl show -p Environment ctf-orchestrator-api.service | grep SIGNING_SECRET
  
  # Client: use that exact secret value
  ```

- **If signature format wrong:**
  Ensure `X-Signature-Timestamp` is Unix timestamp (numeric only):
  ```bash
  # Correct
  X-Signature-Timestamp: 1234567890
  
  # Wrong
  X-Signature-Timestamp: Fri Apr 04 12:34:56 UTC 2026
  ```

---

### Issue 5: Audit Logs Not Recording

**Symptoms:**
```
$ vagrant ssh -- sudo tail /var/log/ctf/orchestrator-audit.log
/var/log/ctf/orchestrator-audit.log: No such file or directory
```

**Diagnosis:**

1. Check if log directory exists:
   ```bash
   vagrant ssh -- ls -la /var/log/ctf/
   ```

2. Check if orchestrator API has write permissions:
   ```bash
   vagrant ssh -- sudo namei -l /var/log/ctf/orchestrator-audit.log
   ```

3. Check API logs for errors:
   ```bash
   vagrant ssh -- sudo journalctl -u ctf-orchestrator-api.service -n 100 | tail -20
   ```

**Solutions:**

- **If directory missing:**
  ```bash
  vagrant ssh -- sudo mkdir -p /var/log/ctf
  vagrant ssh -- sudo chmod 750 /var/log/ctf
  vagrant ssh -- sudo chown nobody:nogroup /var/log/ctf
  ```

- **If permissions wrong:**
  ```bash
  vagrant ssh -- sudo chmod 750 /var/log/ctf
  vagrant ssh -- sudo chown nobody:nogroup /var/log/ctf
  ```

- **Re-provision to create directory:**
  ```bash
  vagrant provision
  ```

- **After fixing, restart API:**
  ```bash
  vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service
  ```

---

### Issue 6: Rate Limiting Not Working

**Symptoms:**
- Making 100 requests rapidly, all succeed (should reject after 60/min per client)
- Per-team quota not enforced (should reject after 3 concurrent instances)

**Diagnosis:**

1. Check rate limit settings:
   ```bash
   vagrant ssh -- sudo systemctl show -p Environment ctf-orchestrator-api.service | grep RATE
   ```

2. Check if rate-limit headers in response:
   ```bash
   curl -v -H "X-Orchestrator-Token: ChangeMe-Orchestrator-Token" http://127.0.0.1:8181/status 2>&1 | grep -i rate
   ```

3. Verify team_id is being extracted from token:
   ```bash
   # Check API source code
   cat /opt/ctf/scripts/player-instance-api.py | grep -A5 "def get_team_id"
   ```

**Solutions:**

- **If rate limits too high/low**, edit `/opt/ctf/scripts/player-instance-api.py`:
  ```python
  # Line ~50:
  RATE_LIMIT_PER_MINUTE = 60  # per client
  TEAM_RATE_LIMIT_PER_MINUTE = 30  # per team
  ```
  Then restart:
  ```bash
  vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service
  ```

- **If team_id extraction wrong**, verify token format matches code logic

---

### Issue 7: X-Forwarded-For Headers Not Working

**Symptoms:**
- Audit logs show client IP as "127.0.0.1" even though request came from external IP
- Rate limiting treats all external requests as same client

**Cause:** nginx not forwarding X-Forwarded-For headers, or orchestrator API not reading them.

**Diagnosis:**

1. Check if nginx is forwarding headers:
   ```bash
   curl -v http://127.0.0.1:8181/status 2>&1 | grep -i x-forwarded
   ```

2. Check nginx config:
   ```bash
   vagrant ssh -- cat /etc/nginx/sites-enabled/orchestrator-api.conf | grep -E 'proxy_set_header.*X-'
   ```
   Expected:
   ```
   proxy_set_header X-Real-IP $remote_addr;
   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
   ```

3. Check if API is using X-Forwarded-For:
   ```bash
   vagrant ssh -- cat /opt/ctf/scripts/player-instance-api.py | grep -i x-forwarded
   ```

**Solutions:**

- **If nginx config missing headers:**
  Re-provision:
  ```bash
  vagrant provision
  ```

- **If API not reading headers:**
  Check that this code exists in API:
  ```python
  def get_client_ip():
      return request.headers.get('X-Forwarded-For', '0.0.0.0').split(',')[0].strip()
  ```

---

### Issue 8: CTFd Event Endpoint Not Responding

**Symptoms:**
```
$ curl -X POST http://127.0.0.1:8181/ctfd/event
{"ok": false, "error": "..."}
```

**Diagnosis:**

1. Check if endpoint exists:
   ```bash
   curl -i http://127.0.0.1:8181/ctfd/event
   ```
   Expected: 400 Bad Request (missing event body), NOT 404

2. Check if webhook token is required:
   ```bash
   curl -X POST http://127.0.0.1:8181/ctfd/event -H "Content-Type: application/json" -d '{"event": "challenge.start"}'
   ```

3. Check API logs:
   ```bash
   vagrant ssh -- sudo journalctl -u ctf-orchestrator-api.service -n 50 | grep ctfd
   ```

**Solutions:**

- **If endpoint returns 404:**
  Check if API was redeployed with new code containing /ctfd/event:
  ```bash
  vagrant provision
  vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service
  ```

- **If missing webhook token header:**
  Provide the header:
  ```bash
  curl -X POST http://127.0.0.1:8181/ctfd/event \
    -H "Content-Type: application/json" \
    -H "X-CTFd-Webhook-Token: ChangeMe-CTFd-Webhook-Token" \
    -d '{"event": "challenge.start", "team_id": "1", "challenge_id": "web-01"}'
  ```

---

## Restart Procedures

### Full Service Restart

```bash
# Restart orchestrator API
vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service

# Restart nginx
vagrant ssh -- sudo systemctl restart nginx

# Verify both running
vagrant ssh -- sudo systemctl status ctf-orchestrator-api.service
vagrant ssh -- sudo systemctl status nginx
```

### Graceful Reload (no downtime)

```bash
# Reload nginx config without dropping connections
vagrant ssh -- sudo systemctl reload nginx

# Reload orchestrator (simulated)
vagrant ssh -- sudo systemctl reload-or-restart ctf-orchestrator-api.service
```

### Full Vagr Provision

If issues persist, re-provision everything:

```bash
vagrant provision
```

This will:
- Re-deploy all templates
- Restart all services
- Fix any configuration drift

---

## Monitoring in Production

### Health Check Endpoint

Add to monitoring/alerting (Prometheus, Nagios, etc.):

```bash
# Should always return 200 with simple response
curl -s http://127.0.0.1:8181/health || alert "Orchestrator API down"
```

### Log Monitoring

Monitor audit logs for suspicious activity:

```bash
# Watch for failed signature attempts
vagrant ssh -- tail -f /var/log/ctf/orchestrator-audit.log | grep signature_rejected

# Count errors per hour
vagrant ssh -- grep error /var/log/ctf/orchestrator-audit.log | tail -n 3600 | wc -l
```

### Performance Metrics

Monitor rate limit behavior:

```bash
# Check if clients are hitting rate limits
vagrant ssh -- grep "rate_limited" /var/log/ctf/orchestrator-audit.log | tail -n 20
```

---

## Emergency Procedures

### API Hanging / Slow Response

```bash
# Kill unresponsive process
vagrant ssh -- sudo pkill -f player-instance-api.py

# Restart
vagrant ssh -- sudo systemctl restart ctf-orchestrator-api.service
```

### nginx Consuming Too Much Memory

```bash
# Check nginx processes
vagrant ssh -- ps aux | grep nginx

# Restart nginx
vagrant ssh -- sudo systemctl restart nginx
```

### Cannot Connect to API After Config Change

```bash
# Check if syntax is valid
vagrant ssh -- sudo nginx -t

# View error log for clues
vagrant ssh -- sudo tail -n 100 /var/log/nginx/error.log

# Force full restart
vagrant ssh -- sudo systemctl restart nginx ctf-orchestrator-api.service
```

---

## Log Locations

| Log | Path | Access |
|-----|------|--------|
| **nginx error** | `/var/log/nginx/error.log` | `sudo tail` |
| **nginx access** | `/var/log/nginx/access.log` | `sudo tail` |
| **Orchestrator API** | `journalctl -u ctf-orchestrator-api.service` | `sudo journalctl` |
| **Audit events** | `/var/log/ctf/orchestrator-audit.log` | `sudo tail` |
| **Orchestrator env** | `/opt/ctf/orchestrator.env` | `sudo cat` |
| **nginx config** | `/etc/nginx/sites-enabled/orchestrator-api.conf` | `sudo cat` |

---

## Support

- **nginx docs:** https://nginx.org/en/docs/
- **systemd docs:** https://systemd.io/
- **Orchestrator API source:** [scripts/player-instance-api.py](../scripts/player-instance-api.py)
