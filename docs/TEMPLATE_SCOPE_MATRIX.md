# Template Scope Matrix (EN)

This matrix defines what belongs in the baseline template versus what should live in a custom repository.

## Scope Buckets

- Core Template: required for a reusable baseline and should stay enabled.
- Optional Template Module: useful for many teams, but should stay configurable.
- Custom Repository Only: organization-specific customizations, experiments, or branding.

## Matrix

| Area | Current Status | Bucket | Action |
|---|---|---|---|
| Vagrant + Ansible provisioning | Stable and reusable | Core Template | Keep as-is |
| CTFd Docker Compose deployment | Stable and reusable | Core Template | Keep as-is |
| Orchestrator API security controls | Reusable and key value | Core Template | Keep enabled by default |
| Challenge family templates (`challenges/_templates`) | Reusable starter content | Core Template | Keep as-is |
| Challenge validation scripts | Reusable quality gate | Core Template | Keep as-is |
| Plugin lifecycle routes (`/start`, `/stop`, `/extend`, `/instances`) | Reusable platform behavior | Core Template | Keep as-is |
| Plugin UI theme details | Team preference dependent | Optional Template Module | Keep functional, avoid heavy branding |
| Monitoring docs | Useful but not mandatory | Optional Template Module | Keep documented as optional |
| Kubernetes extension docs | Advanced path, not baseline | Optional Template Module | Keep documented as optional |
| Direct DB patch script (`scripts/fix_ctfd_challenge_links.py`) | Legacy operational shortcut | Excluded from baseline template | Keep only in custom/operator repo if needed |
| Legacy SQL patch (`scripts/fix_ctfd_links.sql`) | Legacy/manual fix | Excluded from baseline template | Keep only in custom/operator repo if needed |
| Team-specific runbooks | Operator-specific | Custom Repository Only | Keep in custom repo docs |

## Baseline Acceptance Criteria

A baseline template release is accepted when:

1. A new user can run provisioning from scratch and reach CTFd + orchestrator endpoints.
2. Challenge creation/validation works on Windows and Linux/macOS.
3. Security preflight and CI checks pass without editing source code.
4. Core plugin flows (launch, status, extend, stop) work with default configuration.
5. No workflow depends on local direct DB patch scripts.

## Policy

- New feature proposals must declare one of the three scope buckets.
- Features in `Custom Repository Only` should not be required by template docs.
- Template docs stay EN-only and platform-agnostic where possible.
