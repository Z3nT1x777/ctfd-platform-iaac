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
