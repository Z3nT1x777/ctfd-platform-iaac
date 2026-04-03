# Pwn Challenge Template

Use this template for Docker-based binary exploitation challenges.

## Required Files

- `challenge.yml`
- `Dockerfile`
- `docker-compose.yml`
- challenge runtime assets (binary, launcher, support files)
- `flag.txt`

## Workflow

1. Generate challenge directory from this family template.
2. Add binary and runtime dependencies.
3. Define a stable network port mapping.
4. Validate structure with project scripts.
5. Run and test exploitation path in the VM.

## Runtime Notes

- Pin toolchain and runtime package versions when possible.
- Keep challenge state resettable between runs.
- Ensure challenge metadata reflects architecture and difficulty.
