# Challenge Family Templates

This directory contains the canonical scaffolds used to create new challenges.

## Available Families

- `web`: Docker-based web challenge
- `osint`: static challenge, no container runtime
- `sandbox`: Docker-based sandbox challenge
- `reverse`: Docker-based reverse engineering challenge
- `pwn`: Docker-based binary exploitation challenge

## Generation Commands

Windows:

```powershell
./scripts/new-challenge.ps1 -Name <name> -Family <family>
```

Linux/macOS:

```bash
bash ./scripts/new-challenge.sh <name> --family <family>
```

## Validation

Always validate generated challenges before opening a pull request:

- Windows: `./scripts/validate-challenge.ps1 -Path challenges/<name>`
- Linux/macOS: `bash ./scripts/validate-challenge.sh challenges/<name>`

## Access Mode Metadata (Recommended)

To keep front-end launch behavior coherent across mixed challenge types,
you can add optional metadata in `challenge.yml`:

- `connection_mode: web|ssh|instruction|auto`
- `ssh_user: <username>` for SSH command rendering
- `access_instructions: <text>` for non-web/non-ssh instructions
- `container_port: <port>` when the runtime listens on a non-default internal port (for example SSH on `22`)

The plugin uses runtime signals + these hints to render either:
- a web button,
- SSH commands to copy,
- or instruction text.

Example guidance:
- Web challenge: `connection_mode: web`
- SSH/VM challenge: `connection_mode: ssh`, `ssh_user: ctf`, `container_port: 22`
- OSINT/static challenge: `connection_mode: instruction`
