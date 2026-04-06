# Repository Content Guidelines (EN)

This guide defines how content is organized inside the single custom repository.

## Content Zones

| Zone | What belongs here | What must not be committed |
|---|---|---|
| Core platform | Vagrant/Ansible provisioning, CTFd deployment, orchestrator runtime, shared scripts | Machine-local hacks and temporary debug edits |
| Challenge layer | `challenges/` content, family starters in `challenges/_templates`, validation scripts | Real flags, production credentials, private writeups |
| Operations docs | Deployment, troubleshooting, monitoring, security procedures | Outdated fork/template strategy notes |

## Documentation Rules

- Keep docs aligned with the current custom runtime only.
- Prefer one authoritative page per topic, then link to it.
- Remove or rewrite historical notes that describe old fork/upstream workflows.
- Keep examples executable as written on a fresh clone.

## Script and Automation Rules

- Scripts in `scripts/` must be reusable and idempotent when possible.
- One-off operator fixes should include a clear warning banner.
- Any script that mutates live data must include dry-run guidance.

## Review Questions

Before merging changes, check:

1. Is this still correct for `ctfd-platform-custom` as deployed?
2. Does it avoid references to deprecated repos/forks?
3. Can a new teammate run this without hidden local context?
4. Are secrets and sensitive values excluded from git?
