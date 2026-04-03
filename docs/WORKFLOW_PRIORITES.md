# Workflow Priorise - CTF Platform

## P0 - Stabiliser l'infrastructure
Objectif: un `vagrant up` reproductible pour toute l'equipe.

Commandes:

```bash
vagrant up --provision
vagrant status
vagrant ssh -c "docker ps"
vagrant ssh -c "curl -I http://localhost"
```

Criteres de validation:
- VM en etat `running`
- Containers `ctfd`, `ctfd_db`, `ctfd_cache` actifs
- CTFd repond en HTTP (302 vers `/setup` ou 200)

## P1 - Industrialiser l'ajout de challenges
Objectif: creation de challenge en moins de 10 minutes sans erreur de structure.

1. Creer un challenge depuis le template via script.
2. Modifier code et metadata (`challenge.yml`).
3. Lancer la validation locale avant commit.
4. Tester le challenge dans la VM.

Le dossier `challenges/_templates` contient les squelettes officiels par famille (`web`, `osint`, `sandbox`, `reverse`, `pwn`).

Commandes Windows:

```powershell
./scripts/new-challenge.ps1 -Name web-01-sqli -Family web
./scripts/validate-challenge.ps1 -Path challenges/web-01-sqli
vagrant ssh -c "cd /vagrant/challenges/web-01-sqli && docker compose up -d --build"
```

Commandes Linux/macOS:

```bash
bash ./scripts/new-challenge.sh web-01-sqli --family web
bash ./scripts/validate-challenge.sh challenges/web-01-sqli
vagrant ssh -c "cd /vagrant/challenges/web-01-sqli && docker compose up -d --build"
```

## P2 - Workflow Git et PR
Objectif: eviter les conflits et garder un historique lisible.

```bash
git checkout main
git pull --rebase origin main
git checkout -b feat/challenge-web-01-sqli
# edits...
git add challenges/web-01-sqli
git commit -m "feat(challenge): add web-01-sqli"
git push -u origin feat/challenge-web-01-sqli
```

Checklist PR:
- Description du challenge
- Port expose et non-conflictuel
- Validation script passee
- Test runtime dans VM valide

## P3 - Durcissement securite
Objectif: aligner l'infra avec un niveau M2 solide.

Statut actuel:

1. Support Ansible Vault ajoute via `ansible/vars/vault.yml` (override des defaults).
2. Security preflight CI en place (`.github/workflows/security-preflight.yml`).
3. API orchestrator renforcee: signature HMAC, quotas par equipe, rate limiting, logs d'audit.
4. Trigger CTFd disponible via endpoint `POST /ctfd/event`.
