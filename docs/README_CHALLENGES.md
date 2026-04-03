# Challenge Workflow Guide

This guide explains how to create, validate, and deploy a challenge on each supported OS.

## Purpose of `challenges/_template`

The folder [challenges/_template](../challenges/_template) is the canonical scaffold for new challenges.

- Copy it for every new challenge.
- Do not deploy it directly.
- Keep it as the shared base so the team works with the same structure.

Expected files inside a challenge folder:

- `Dockerfile`
- `app.py`
- `flag.txt`
- `requirements.txt`
- `docker-compose.yml`
- `challenge.yml`

## Windows workflow

### 1. Create a challenge

```powershell
Set-Location "C:/Users/Ozen/Documents/ctf-platform-iaac-main/ctf-platform-iaac-main"
./scripts/new-challenge.ps1 -Name web-01-test
```

Optional explicit port:

```powershell
./scripts/new-challenge.ps1 -Name web-01-test -Port 5001
```

### 2. Validate the structure

```powershell
./scripts/validate-challenge.ps1 -Path challenges/web-01-test
```

### 3. Start the challenge in the VM

```powershell
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

### 4. Test in browser

- Open `http://192.168.56.10:5001`
- Or `http://localhost:5001` if you use forwarded ports

## Linux and macOS workflow

### 1. Create a challenge

```bash
cd /path/to/ctf-platform-iaac-main
bash ./scripts/new-challenge.sh web-01-test
```

Optional explicit port:

```bash
bash ./scripts/new-challenge.sh web-01-test --port 5001
```

### 2. Validate the structure

```bash
bash ./scripts/validate-challenge.sh challenges/web-01-test
```

### 3. Start the challenge in the VM

```bash
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

### 4. Test in browser

- Open `http://192.168.56.10:5001`
- Or `http://localhost:5001` if your setup forwards the port

## What the challenge files do

- `app.py`: application logic for the challenge.
- `flag.txt`: the flag used by the challenge logic.
- `Dockerfile`: builds the container image.
- `requirements.txt`: Python dependencies if the challenge needs them.
- `docker-compose.yml`: local runtime definition for the challenge container.
- `challenge.yml`: metadata used by the team to track the challenge.

## Manual creation if you do not use the helper scripts

1. Copy `challenges/_template` to a new folder.
2. Rename the folder.
3. Edit `challenge.yml`.
4. Edit `app.py`, `Dockerfile`, and `requirements.txt`.
5. Set a free port in `docker-compose.yml`.
6. Validate the folder.
7. Start it in the VM.

## Recommended rules for the team

- Use one port per challenge.
- Keep `flag.txt` consistent with the flag expected by the app.
- Never reuse the same challenge folder for multiple different ideas.
- Use the helper scripts before commit to catch structure mistakes.

## Notes on CTFd

- The first admin account is created through the CTFd setup wizard.
- Once CTFd is initialized, you can add users and challenges from the admin interface.
- If you need to reset the setup during testing, remove the persisted data carefully.

## Security reminder

- `.env` is local-only and must not be committed.
- `ansible/vars/main.yml` still contains development defaults.
- For a stronger security baseline, migrate sensitive values to Ansible Vault later.
