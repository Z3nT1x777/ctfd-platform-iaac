# Challenge Workflow Guide

This document defines the standard process to create, validate, and run challenges in this repository.

## Template Source

Challenge templates are maintained in [challenges/_templates](../challenges/_templates), grouped by family:

- `web` (docker)
- `osint` (static)
- `sandbox` (docker)
- `reverse` (docker)
- `pwn` (docker)

Do not deploy folders under `_templates` directly. Always generate a dedicated challenge directory first.

## Required Structure

Docker challenge minimum files:

- `challenge.yml`
- `Dockerfile`
- `docker-compose.yml`
- `app.py`
- `flag.txt`
- `requirements.txt`

Static challenge minimum files (for example `osint`):

- `challenge.yml`
- `README.md`
- optional resources (documents, images, evidence sets)

## Standard Workflow (Windows)

1. Create a challenge:

```powershell
./scripts/new-challenge.ps1 -Name web-01-test -Family web
```

2. Validate structure:

```powershell
./scripts/validate-challenge.ps1 -Path challenges/web-01-test
```

3. Run challenge in VM:

```powershell
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

## Standard Workflow (Linux/macOS)

1. Create a challenge:

```bash
bash ./scripts/new-challenge.sh web-01-test --family web
```

2. Validate structure:

```bash
bash ./scripts/validate-challenge.sh challenges/web-01-test
```

3. Run challenge in VM:

```bash
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

## Validation Layers

- Local validation scripts:
	- `scripts/validate-challenge.ps1`
	- `scripts/validate-challenge.sh`
- CI validation workflow:
	- `.github/workflows/challenge-validation.yml`
	- `scripts/validate_challenges_ci.py`

## Team Conventions

- Use a unique challenge identifier and unique port mapping for docker challenges.
- Keep challenge metadata (`challenge.yml`) consistent with runtime implementation.
- Validate before opening any pull request.
- Keep challenge directories immutable after publication whenever possible.

## CTFd Integration Notes

- CTFd is available after provisioning and setup initialization.
- Challenge runtime containers are independent from CTFd core containers.
- Per-team orchestrated instances are managed separately by the orchestrator manager/API.
