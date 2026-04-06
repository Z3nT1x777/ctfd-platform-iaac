# Template Baseline Plan (EN)

## Goal
Create a reusable private template repository that keeps core CTF platform capabilities while excluding team-specific production customizations.

## Keep In Template
- Reproducible infra (Vagrant + Ansible + Docker Compose)
- CTFd deployment with orchestrator plugin integration
- Security baseline defaults and Vault override model
- Challenge family templates and validation scripts
- CI validation workflows and preflight checks
- Generic player launch/dashboard lifecycle flows

## Move To Custom Repo
- Team branding and highly opinionated UI polish
- Operations runbooks tied to one team workflow
- Aggressive production tuning specific to one environment
- Ad-hoc migration/fix scripts that are not generally reusable

## Hard Rules For Template
- English-only documentation
- No hardcoded secrets (use placeholders + Vault docs)
- Feature-complete but configuration-driven defaults
- Stable public APIs/routes for plugin behavior

## Validation Checklist
- `vagrant up --provision` succeeds on clean machine
- CTFd and orchestrator endpoints reachable
- Challenge create/validate scripts work on Windows and Linux/macOS
- Plugin launch/start/extend/stop flows pass smoke tests
- CI passes on default branch

## Branching Model
- Template repo: conservative changes, release-style updates
- Custom repo: faster iteration, optional features, design experiments
- Sync model: custom repo tracks template repo as upstream
