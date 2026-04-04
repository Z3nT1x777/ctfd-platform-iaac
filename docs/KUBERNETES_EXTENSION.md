# Kubernetes Extension Guide

This guide describes how to extend the current Docker Compose CTF platform to Kubernetes while keeping the same orchestrator workflow.

## Why Kubernetes

Use Kubernetes when you need:
- More than one VM/host
- Better scheduling and resource isolation
- Horizontal scaling during peak tournament traffic
- Built-in rolling updates and self-healing

## Current Model vs Kubernetes

Current runtime:
- CTFd and services on Docker Compose
- Orchestrator starts team instances with `docker compose`
- TTL cleanup via systemd timer

Kubernetes runtime target:
- CTFd as Deployment + Service
- Team instances as Namespaced Deployments/Pods
- TTL cleanup via CronJob/Controller

## Migration Strategy

### Phase 1: Hybrid Mode

- Keep CTFd on Docker Compose
- Replace challenge runtime only with Kubernetes
- Add orchestrator backend adapter (docker -> kubernetes)

### Phase 2: Full K8s

- Move CTFd, Redis, MariaDB/Postgres to K8s manifests/Helm
- Expose services with Ingress + TLS
- Integrate secret management (Sealed Secrets / External Secrets)

## Orchestrator Backend Adapter

Abstract runtime backend in orchestrator:
- `backend=docker` (current default)
- `backend=kubernetes` (new)

Kubernetes backend actions:
- Start: create Namespace or labels per team, apply Deployment/Service
- Stop: delete Deployment/Service
- Status: query pods/services
- Cleanup: remove expired workloads by label + expiry annotation

## Suggested Resource Model

Per team/challenge instance:
- Namespace (optional) or labels: `team_id`, `challenge`, `expire_epoch`
- Deployment: challenge container
- Service: ClusterIP + optional NodePort/Ingress
- NetworkPolicy: deny inter-team traffic

## Security Controls Mapping

Existing control -> Kubernetes equivalent:
- API token/HMAC: unchanged (orchestrator API)
- Team quotas: ResourceQuota + orchestrator checks
- Rate limits: unchanged in API gateway/orchestrator
- Audit logs: API logs + Kubernetes audit logs
- Vault: map to K8s Secrets provider

## Operational Notes

- Keep instance TTL in annotation (e.g. `ctf.expire_epoch`)
- Run cleanup CronJob every 5 minutes
- Add PodDisruptionBudgets for critical services
- Use dedicated node pool for challenge workloads

## Minimal Deliverables to Start

1. Add runtime abstraction in orchestrator manager
2. Implement `start/stop/status/cleanup` for K8s backend
3. Add Helm chart for a sample challenge
4. Add Prometheus scraping for challenge pods
5. Add runbook for failover and rollback

## Recommended Stack

- Kubernetes: k3s (lab) or managed (AKS/EKS/GKE)
- Ingress: NGINX Ingress Controller
- Metrics: Prometheus + Grafana
- Logs: Loki + Promtail or ELK
- Secrets: External Secrets Operator + Vault
