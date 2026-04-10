# Ansible Vault Setup Guide

## Overview

Ansible Vault secures production secrets (database passwords, API signing keys, webhook tokens) without storing them in plaintext in version control. This guide explains how to set up and use Vault with the CTF platform infrastructure.

---

## Secrets Reference

| Secret | Used by | Purpose |
|--------|---------|---------|
| `DB_ROOT_PASSWORD` | MariaDB | Compte root — administration de la base (création users, backups) |
| `DB_PASSWORD` | MariaDB + CTFd | Compte `ctfd` — connexion runtime de l'application à la base |
| `orchestrator_api_token` | Orchestrateur | Header `X-Orchestrator-Token` — authentifie chaque appel API |
| `orchestrator_signing_secret` | Orchestrateur | Clé HMAC-SHA256 pour signer les requêtes POST (anti-replay) |
| `orchestrator_ctfd_webhook_token` | CTFd → Orchestrateur | Authentifie les webhooks envoyés par CTFd vers l'orchestrateur |
| `grafana_admin_password` | Grafana | Mot de passe du compte `admin` Grafana |

> **Important :** `DB_PASSWORD` doit être identique dans le vault ET dans MariaDB. Si vous changez ce secret après la première initialisation, vous devez supprimer `/opt/ctf/ctfd/db_data/` sur la VM et re-provisionner pour que MariaDB soit réinitialisée avec le nouveau mot de passe.

---

## File Structure

```
ansible/
├── vars/
│   ├── main.yml                 # Default values (includes non-sensitive defaults)
│   ├── vault.example.yml        # Template for vault secrets
│   └── vault.yml                # 🔐 ENCRYPTED - not in version control
├── playbooks/
│   └── main.yml                 # Loads vault.yml if it exists
└── ansible.cfg
```

---

## Setup Steps

### 1. Create Vault File from Template

```bash
cd ansible/vars/
cp vault.example.yml vault.yml
```

### 2. Encrypt with Ansible Vault

```bash
ansible-vault encrypt vault.yml
```

You'll be prompted to create a vault password. **Store this password securely** (e.g., separate from repository, in a password manager).

### 3. Edit Vault File

To edit an encrypted vault file:

```bash
ansible-vault edit vault.yml
```

Example content (automatically encrypted — mirrors `vault.example.yml`):

```yaml
# Database secrets
DB_ROOT_PASSWORD: "your-strong-root-password"
DB_PASSWORD: "your-strong-db-password"

# Orchestrator API secrets
orchestrator_api_token: "your-64-char-random-token"
orchestrator_signing_secret: "your-64-char-hmac-secret"
orchestrator_ctfd_webhook_token: "your-webhook-token"

# Monitoring
grafana_admin_password: "your-strong-grafana-password"
```

Generate strong secrets with:

```bash
openssl rand -hex 32   # 64-char hex — for tokens and signing secrets
openssl rand -base64 24  # 32-char base64 — for passwords
```

### 4. Set Up Vault Password File (CI/CD or Automation)

For automated deployments, create a vault password file:

```bash
# Store vault password in secure location (NOT in git)
echo "your-vault-password" > /etc/ansible/vault-password.txt
chmod 600 /etc/ansible/vault-password.txt
```

Then use in ansible commands:

```bash
ansible-playbook playbooks/main.yml --vault-password-file=/etc/ansible/vault-password.txt
```

---

## How It Works

### Playbook Loading (main.yml)

The playbook loads vault.yml **without failing if it doesn't exist** (for development):

```yaml
- name: Load Vault Secrets (optional)
  include_vars: vault.yml
  failed_when: false
  no_log: true
```

### Secret Merging (Effective Variables)

For each secret, the playbook sets an "effective" value, preferring vault overrides:

```yaml
- name: Build effective secret values
  set_fact:
    db_root_password_effective:            "{{ vault_overrides.DB_ROOT_PASSWORD            | default(DB_ROOT_PASSWORD) }}"
    db_password_effective:                 "{{ vault_overrides.DB_PASSWORD                 | default(DB_PASSWORD) }}"
    orchestrator_api_token_effective:      "{{ vault_overrides.orchestrator_api_token      | default(orchestrator_api_token) }}"
    orchestrator_signing_secret_effective: "{{ vault_overrides.orchestrator_signing_secret | default(orchestrator_signing_secret) }}"
    orchestrator_ctfd_webhook_token_effective: "{{ vault_overrides.orchestrator_ctfd_webhook_token | default(orchestrator_ctfd_webhook_token) }}"
    grafana_admin_password_effective:      "{{ vault_overrides.grafana_admin_password      | default(grafana_admin_password) }}"
  no_log: true
```

### Template Usage

Templates use `_effective` variables:

```jinja2
# docker-compose-ctfd.yml.j2
environment:
  DB_ROOT_PASSWORD: "{{ db_root_password_effective }}"
  DB_PASSWORD: "{{ db_password_effective }}"
  ORCHESTRATOR_SIGNING_SECRET: "{{ orchestrator_signing_secret_effective }}"
```

---

## Development vs. Production

### Development (without Vault)

- `vault.yml` does **not** exist
- Playbook uses defaults from `main.yml`
- ✅ Default values: `ChangeMe-*`, `demo-*` (safe for testing)
- ⚠️ **DO NOT use in production**

Command:

```bash
# Development: no vault needed
vagrant provision
```

### Production (with Vault)

- `vault.yml` exists and is encrypted
- Playbook automatically loads and uses vault secrets
- ✅ Sensitive values override defaults
- 🔐 Secrets never stored in plaintext

Command:

```bash
# Production: vault password required
ansible-playbook playbooks/main.yml --vault-password-file=/etc/ansible/vault-password.txt
```

---

## Best Practices

### ✅ DO:

- **Store vault password separately** (not in repo, not in plaintext)
- **Use strong, randomly generated secrets** for production
  ```bash
  # Generate 64-char secret
  openssl rand -hex 32
  ```
- **Encrypt vault.yml** before committing (if you accidentally add it)
  ```bash
  ansible-vault encrypt vault.yml
  ```
- **Use CI/CD secrets management** (GitHub Secrets, GitLab CI Variables, vault-as-a-service)
- **Rotate secrets regularly** in production

### ❌ DON'T:

- **Commit unencrypted vault.yml** to version control  
- **Share vault password in messages or documentation**
- **Use weak passwords** for vault encryption  
- **Disable `no_log: true`** on secret tasks (it hides secrets from Ansible output)
- **Hardcode secrets** in templates or scripts

---

## Troubleshooting

### Vault Password Prompt Hang

If Ansible hangs asking for vault password:

```bash
# Provide password via stdin
echo "your-password" | ansible-playbook playbooks/main.yml --vault-password-file=/dev/stdin

# Or use password file
ansible-playbook playbooks/main.yml --vault-password-file=/etc/ansible/vault-password.txt
```

### "Vault password did not match"

- Vault is asking for the **encryption password** (set when creating vault), not the secret values
- Try again, copy/paste carefully
- If lost, re-create vault.yml (will need new secrets)

### "Decryption failed"

- Vault file is corrupted or using wrong encryption algorithm
- Try viewing it:
  ```bash
  ansible-vault view vault.yml
  ```
- If view fails, re-create or restore from backup

### Secrets Not Overriding Defaults

Check that vault.yml is properly encrypted and loaded:

```bash
# List vars in playbook
ansible-playbook playbooks/main.yml --syntax-check

# View vault file (requires password)
ansible-vault view vault.yml

# Run with verbose output
ansible-playbook playbooks/main.yml -v
```

---

## Integration with CI/CD

### GitHub Actions Example

Store vault password as a GitHub Secret:

```yaml
name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Provision with Vault
        env:
          VAULT_PASSWORD: ${{ secrets.ANSIBLE_VAULT_PASSWORD }}
        run: |
          echo "$VAULT_PASSWORD" > /tmp/vault-pass.txt
          ansible-playbook playbooks/main.yml --vault-password-file=/tmp/vault-pass.txt
          rm /tmp/vault-pass.txt
```

### GitLab CI Example

```yaml
deploy:
  script:
    - echo "$ANSIBLE_VAULT_PASSWORD" > /tmp/vault-pass.txt
    - ansible-playbook playbooks/main.yml --vault-password-file=/tmp/vault-pass.txt
    - rm /tmp/vault-pass.txt
  environment:
    ANSIBLE_VAULT_PASSWORD: $VAULT_PASSWORD
```

---

## Summary

| Scenario | Vault Needed? | Command |
|----------|---------------|---------|
| **Local development** | No | `vagrant provision` |
| **Local testing with secrets** | Yes | `ansible-vault edit vault.yml` then `vagrant provision` |
| **Production deployment** | ✅ **YES** | `ansible-playbook playbooks/main.yml --vault-password-file=/etc/ansible/vault-password.txt` |
| **CI/CD pipeline** | ✅ **YES** | Use CI secrets manager + `--vault-password-file=/dev/stdin` |

---

## Secret Rotation Process

1. Edit vault:
   ```bash
   ansible-vault edit vault.yml
   ```

2. Update the secret value

3. Re-provision infrastructure:
   ```bash
   ansible-playbook playbooks/main.yml --vault-password-file=/etc/ansible/vault-password.txt
   ```

4. Verify service restart:
   ```bash
   vagrant ssh -- sudo systemctl status ctf-orchestrator-api
   ```

---

## Support

For Ansible Vault documentation, see: https://docs.ansible.com/ansible/latest/user_guide/vault.html
