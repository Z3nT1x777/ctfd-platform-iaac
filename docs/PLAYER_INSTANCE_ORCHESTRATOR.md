# Player Instance Orchestrator

This document describes a safe per-team challenge instance model with TTL-based cleanup.

## Goal

Each team/player starts an isolated docker instance of a challenge with a fixed lifetime.
When TTL expires, the instance is stopped and removed automatically.

## Scope of this branch

- Design + PoC CLI manager
- No CTFd plugin wiring yet
- Lifecycle commands available from VM shell

## Script

Path: `scripts/player-instance-manager.sh`

Supported commands:

- `start --challenge <name> --team <team-id> [--ttl-min 60] [--port 6201]`
- `stop --challenge <name> --team <team-id>`
- `status`
- `cleanup`

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

## Next PR (implementation phase)

- Expose manager via a small internal API service.
- Add a timer/service (systemd or cron) for periodic cleanup.
- Integrate with CTFd trigger path (plugin or webhook layer).
- Add audit logs and stronger quota/rate limits.
