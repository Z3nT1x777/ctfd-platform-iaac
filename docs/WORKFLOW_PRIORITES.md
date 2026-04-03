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

Le dossier `challenges/_template` est le squelette officiel. Il ne doit pas etre modifie pour un challenge reel: il sert de base unique pour tous les nouveaux challenges.

Commandes Windows:

```powershell
./scripts/new-challenge.ps1 -Name web-01-sqli
./scripts/validate-challenge.ps1 -Path challenges/web-01-sqli
vagrant ssh -c "cd /vagrant/challenges/web-01-sqli && docker compose up -d --build"
```

Commandes Linux/macOS:

```bash
bash ./scripts/new-challenge.sh web-01-sqli
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

1. Migrer les credentials de `ansible/vars/main.yml` vers Ansible Vault.
2. Definir une politique de rotation des secrets `.env`.
3. Ajouter un job CI de validation de structure des challenges.
