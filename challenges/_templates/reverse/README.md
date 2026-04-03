# Reverse Challenge Template

Use this template for Docker-based reverse engineering challenges.

## Required Files

- `challenge.yml`
- `Dockerfile`
- `docker-compose.yml`
- challenge artifacts (binary, archive, symbols when applicable)
- `flag.txt`

## Workflow

1. Generate challenge directory from the reverse template.
2. Add challenge artifacts and execution logic.
3. Validate challenge structure.
4. Start challenge in VM and verify expected solving flow.

## Runtime Notes

- Keep binaries and dependencies deterministic.
- Document challenge objective and expected output in metadata.
- Verify that runtime configuration matches distributed artifacts.
