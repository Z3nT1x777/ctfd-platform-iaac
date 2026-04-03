# Player Instance Orchestrator

This document describes a safe per-team challenge instance model with TTL-based cleanup.

## Goal

Each team/player starts an isolated docker instance of a challenge with a fixed lifetime.
When TTL expires, the instance is stopped and removed automatically.

## Scope of this branch

- Design + PoC CLI manager
- Implementation layer with local HTTP API
- Automatic cleanup timer deployed via Ansible/systemd

## Script

Path: `scripts/player-instance-manager.sh`

Supported commands:

- `start --challenge <name> --team <team-id> [--ttl-min 60] [--port 6201]`
- `stop --challenge <name> --team <team-id>`
- `status`
- `cleanup`

API path: `scripts/player-instance-api.py`

HTTP endpoints:

- `GET /ui`
- `GET /health`
- `GET /status`
- `POST /start`
- `POST /stop`
- `POST /cleanup`

Authentication:

- `Authorization: Bearer <token>`
- or `X-Orchestrator-Token: <token>`

Rate limiting:

- in-memory limit per client (IP / forwarded IP)
- configured by `ORCHESTRATOR_RATE_LIMIT_PER_MIN`

## Runtime model

- Source challenge dir: `/vagrant/challenges/<challenge>`
- Instance dir: `/opt/ctf/instances/inst_<challenge>_<team>`
- Lease file: `/opt/ctf/leases/inst_<challenge>_<team>.env`
- Port range for player instances: `6100-6999`

A lease file contains challenge, team, project name, mapped port, and expiration epoch.

## Example flow

```bash
# inside the VM
cd /vagrant
bash ./scripts/player-instance-manager.sh start --challenge web-01-test --team team-alpha --ttl-min 60
bash ./scripts/player-instance-manager.sh status
bash ./scripts/player-instance-manager.sh cleanup
bash ./scripts/player-instance-manager.sh stop --challenge web-01-test --team team-alpha
```

## Security and stability constraints

- Team/challenge identifiers are sanitized.
- Only `type: docker` challenges are supported by the manager.
- Dedicated compose project per team/challenge to avoid collisions.
- Fixed instance root (`/opt/ctf/instances`) and lease root (`/opt/ctf/leases`).
- Cleanup only targets managed lease files.

## Deployment integration

Ansible deploys the manager and API in `/opt/ctf/orchestrator` and installs:

- `player-instance-api.service`
- `player-instance-cleanup.service`
- `player-instance-cleanup.timer`

After `vagrant provision`, API listens on VM port `8181`.

UI:

- `http://192.168.56.10:8181/ui`
- provides start/stop/status controls and TTL display

Example call from host:

```bash
curl -X POST http://192.168.56.10:8181/start \
	-H 'Authorization: Bearer ChangeMe-Orchestrator-Token' \
	-H 'Content-Type: application/json' \
	-d '{"challenge":"web-01-test","team":"team-alpha","ttl_min":60}'
```

## Next hardening step

- Integrate with CTFd trigger path (plugin or webhook layer).
- Add audit logs, quotas, and team-level rate limits.
- Add signed request validation for API callers.
