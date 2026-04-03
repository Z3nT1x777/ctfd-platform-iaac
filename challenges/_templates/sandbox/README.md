# Sandbox Challenge Template

Use this template for isolated Docker-based sandbox challenges.

## Required Files

- `challenge.yml`
- `Dockerfile`
- `docker-compose.yml`
- challenge runtime files
- `flag.txt`

## Workflow

1. Generate challenge directory from this template.
2. Implement sandbox logic and runtime constraints.
3. Validate structure before commit.
4. Build and run inside the VM.

## Runtime Notes

- Enforce strict isolation assumptions in container runtime.
- Keep all required resources in repository-controlled paths.
- Confirm challenge start and cleanup behavior before PR submission.
