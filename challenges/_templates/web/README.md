# Web Challenge Template

Use this template for Docker-based web challenges.

## Required Files

- `challenge.yml`
- `Dockerfile`
- `docker-compose.yml`
- `app.py`
- `flag.txt`
- `requirements.txt`

## Workflow

1. Generate challenge directory with helper scripts.
2. Update challenge metadata and runtime code.
3. Validate structure locally.
4. Build and run in the VM with Docker Compose.

## Runtime Notes

- Use a unique host port in `docker-compose.yml`.
- Keep the application deterministic and reproducible.
- Avoid external dependencies that cannot be reproduced during deployment.
