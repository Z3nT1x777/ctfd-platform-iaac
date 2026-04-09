# Monitoring & Observability Guide

**Purpose:** Enable Prometheus metrics collection and Grafana dashboards for CTF infrastructure visibility during tournament operations.

**Status:** ✅ Enabled by default in provisioning (Prometheus + Grafana + Node Exporter + cAdvisor)

---

## Overview

The CTF platform supports enterprise-grade monitoring via:
- **Prometheus:** Time-series database for metrics collection (port 9090)
- **Grafana:** Visualization & alerting dashboards (port 3000)
- **Node Exporter:** Host-level metrics (CPU, memory, disk, network)
- **cAdvisor:** Docker container metrics

This enables real-time visibility of:
- Orchestrator API health & performance
- Docker container resource usage (per-team instances)
- TTL cleanup events and instance lifecycle
- CTFd platform performance
- System resource saturation

---

## Quick Start: Start Monitoring

### Step 1: Re-provision VM

```bash
vagrant provision
```

This will:
- Deploy `docker-compose-monitoring.yml` to `/opt/ctf/monitoring/`
- Deploy `prometheus.yml` to `/opt/ctf/monitoring/prometheus.yml`
- Start Prometheus, Grafana, Node Exporter, cAdvisor containers
- Expose metrics on ports 9090 (Prometheus), 3000 (Grafana)

### Step 2: Access Dashboards

After provisioning (wait 10-15 seconds for services to start):

**Prometheus UI:** http://192.168.56.10:9090
- Browse available metrics
- Query engine for ad-hoc analysis
- Example: `container_memory_usage_bytes{name=~"ctf.*"}`

**Grafana UI:** http://192.168.56.10:3000
- Default credentials: `admin:admin` — **override `grafana_admin_password` in vault before production**
- Prometheus data source auto-provisioned (no manual setup required)
- CTF Operations dashboard pre-loaded (CPU, Memory, Disk, Containers)

---

## Monitoring Architecture

```
Infrastructure
├─ Prometheus (9090)
│  ├─ Scrapes: node-exporter (system metrics)
│  ├─ Scrapes: cAdvisor (container metrics)
│  ├─ Scrapes: orchestrator API (/metrics endpoint, TBD)
│  └─ Storage: 15 GB retention by default
│
├─ Grafana (3000)
│  ├─ Datasource: Prometheus
│  ├─ Dashboards: System, Docker, Orchestrator
│  ├─ Alerting: Channel integration (Slack, PagerDuty, etc.)
│  └─ Access: http://192.168.56.10:3000
│
├─ Node Exporter (on host)
│  └─ CPU, memory, disk, network metrics
│
└─ cAdvisor (on host)
   └─ Per-container resource usage
```

---

## Key Metrics During Tournament

### System Health

**CPU Usage:**
```
cpu_usage = 100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```
Alert if > 80% sustained → scale infrastructure or limit new instances

**Memory Usage:**
```
memory_used_percent = (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
```
Alert if > 85% → OOM killer may trigger

**Disk Usage:**
```
disk_used_percent = (node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100
```
Alert if > 90% → Docker runs out of space for instances

### Docker Container Metrics

**Per-Team Instance Memory:**
```
container_memory_usage_bytes{name=~"ctf_.*_team_.*"}
```
Monitor for memory leaks or runaway processes

**Per-Team Instance CPU:**
```
rate(container_cpu_usage_seconds_total{name=~"ctf_.*_team_.*"}[1m]) * 100
```
Detect CPU-bound challenges consuming resources

**Container Count (Active Instances):**
```
count(container_last_seen{name=~"ctf_.*"}) by (instance)
```
Verify quotas are working: should never exceed max_active * num_teams

### Orchestrator API Metrics

**Active Instances per Team:**
```
count(orchestrator_instances{}) by (team)
```
Monitor team distribution, detect hotspots

**Instance Spawn Time:**
```
orchestrator_instance_spawn_time_seconds (histogram)
```
Track performance degradation as CTF scales

**Start Endpoint Response Time:**
```
rate(orchestrator_request_duration_seconds_bucket{endpoint="/start"}[1m])
```
SLA tracking: should complete in < 5 seconds

**Rate Limit Hits:**
```
orchestrator_rate_limit_exceeded_total
```
Track clients/teams approaching limits

---

## Setting Up Dashboards

### Option 1: Quick Start (Grafana Alerts Only)

Add alert rules in Grafana UI:

```
Alert Name: "High Memory Usage"
Condition: memory_used_percent > 85
For: 5 minutes
Action: Send notification to ops team
```

### Option 2: Import Pre-built Dashboards

Grafana has community dashboards for Docker monitoring:

1. Go to **Dashboards → Import**
2. Search ID: `893` (Docker Monitoring)
3. Select Prometheus as data source
4. Import

Common dashboard IDs:
- `1860`: Node Exporter (System metrics)
- `893`: Docker Monitoring (Container metrics)
- `3146`: Prometheus (Prometheus internal metrics)

### Option 3: Create Custom Dashboard

1. **Dashboards → New Dashboard**
2. **Add Panel → Prometheus**
3. Query: `container_memory_usage_bytes{name=~"ctf_.*"}`
4. Visualization: Graph or Gauge
5. Set title/labels/thresholds
6. Save

Example panels to create:

**Panel 1: Active Instances**
```
Query: count(container_last_seen{name=~"ctf_.*"})
Type: Stat
Thresholds: Green < 30, Yellow < 50, Red ≥ 60
```

**Panel 2: CPU Usage**
```
Query: avg(rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100
Type: Gauge
Unit: percent
Thresholds: Green < 50, Yellow < 80, Red ≥ 80
```

**Panel 3: Memory Usage**
```
Query: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
Type: Gauge
Unit: percent
Thresholds: Green < 60, Yellow < 80, Red ≥ 85
```

**Panel 4: Instances by Team (Stack)**
```
Query: count(container_last_seen{name=~"ctf_team_(.*)_"}) by (team)
Type: Graph (Stacked)
Legend: Team names
```

---

## Production Deployment Checklist

### Before Tournament

- [ ] `vault.yml` has a strong `grafana_admin_password` (not `admin`)
- [ ] `vagrant provision` completed successfully
- [ ] Prometheus scrape targets showing "UP" (http://192.168.56.10:9090/targets)
- [ ] Grafana accessible, data flowing (http://192.168.56.10:3000)
- [ ] CTF Operations dashboard visible in Grafana → Dashboards → CTF folder
- [ ] Grafana default password changed (or confirmed vault override is active)
- [ ] Retention configured as needed (default: 15 days — adjust in docker-compose template)

### During Tournament

**Every 30 minutes (automated via Grafana alerts):**
- [ ] Check CPU usage < 85%
- [ ] Check memory usage < 85%
- [ ] Check disk usage < 90%
- [ ] Verify active instances within quota limits
- [ ] No failed container restarts

**On-demand troubleshooting:**
- Check orchestrator response times (should be < 5s)
- Monitor per-team instance count (distribution)
- Track rate limit hit frequency
- Watch for cascading failures or memory leaks

### After Tournament

- [ ] Backup Prometheus data: `docker exec prometheus tar czf prometheus-backup.tar.gz /prometheus`
- [ ] Export Grafana dashboards for next event
- [ ] Analyze metrics: peak load, resource patterns, bottlenecks
- [ ] Document findings for next tournament scaling

---

## Troubleshooting Monitoring

### Issue 1: Prometheus Shows "No Data"

**Symptom:**
```
Prometheus → Targets: all showing "DOWN"
```

**Diagnosis:**

```bash
vagrant ssh -- sudo docker ps | grep prometheus
vagrant ssh -- sudo docker logs prometheus
```

**Fix:**

```bash
vagrant ssh -- sudo docker-compose -f /opt/ctf/monitoring/docker-compose.yml restart
```

---

### Issue 2: Grafana Dashboards Empty

**Symptom:**
```
Grafana shows empty graphs, "NO DATA" message
```

**Diagnosis:**

1. Check Prometheus connectivity:
   - Grafana → Configuration → Data Sources → Prometheus
   - Click "Test" - should show version

2. Verify metrics are being scraped:
   - Go to Prometheus http://192.168.56.10:9090/graph
   - Query: `up` (should show targets with value=1)

**Fix:**

```bash
# Check if containers are running
vagrant ssh -- sudo docker ps | grep -E 'prometheus|grafana|cadvisor|node-exporter'

# If missing, restart monitoring stack
vagrant ssh -- sudo docker-compose -f /opt/ctf/monitoring/docker-compose.yml up -d
```

---

### Issue 3: Memory / Disk Alert Spam

**Symptom:**
```
Grafana constantly alerting for available resources
```

**Diagnosis:**

Prometheus retention or scrape interval too aggressive:

```bash
# Check Prometheus config
vagrant ssh -- docker exec prometheus cat /etc/prometheus/prometheus.yml | grep -E 'scrape_interval|retention'
```

**Fix:**

Edit `ansible/vars/main.yml`:

```yaml
prometheus_retention_days: 7       # Reduce from 15
prometheus_scrape_interval: 60s    # Increase from 30s
```

Re-provision:

```bash
vagrant provision
```

---

## Integration with Orchestrator API

### Exposing Orchestrator Metrics (Future Enhancement)

To monitor orchestrator performance, add Prometheus metrics endpoint to API:

```python
# Add to player-instance-api.py

from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest

# Metrics
requests_total = Counter('orchestrator_requests_total', 'Total requests', ['endpoint', 'status'])
response_time_seconds = Histogram('orchestrator_response_time_seconds', 'Response time', ['endpoint'])
active_instances = Gauge('orchestrator_active_instances', 'Active instances', ['team'])

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
```

Then add to Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'orchestrator'
    static_configs:
      - targets: ['127.0.0.1:18181']
    metrics_path: '/metrics'
```

---

## References

- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- cAdvisor: https://github.com/google/cadvisor
- Node Exporter: https://github.com/prometheus/node_exporter

---

## Next Steps

1. ✅ Enable monitoring stack (Prometheus + Grafana + Node Exporter + cAdvisor)
2. ✅ Prometheus datasource auto-provisioned on first `vagrant provision`
3. ✅ CTF Operations dashboard auto-loaded (VM + container metrics)
4. ✅ Grafana admin password via Ansible Vault (`grafana_admin_password`)
5. ⚠️ Set up Grafana alerting channels if needed (Slack, email — out of scope for this platform)
6. ⚠️ Add orchestrator API `/metrics` endpoint (P6 — future enhancement)
