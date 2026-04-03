# 🚩 CTF Platform - Infrastructure as Code

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Vagrant](https://img.shields.io/badge/Vagrant-2.4%2B-blue)](https://www.vagrantup.com/)
[![Ansible](https://img.shields.io/badge/Ansible-2.14%2B-red)](https://www.ansible.com/)

## 📋 Projet
Plateforme CTF self-hosted complètement automatisée avec isolation Docker par challenge.  
**Projet M2 Cybersécurité** - Infrastructure as Code & DevSecOps.

### ✨ Caractéristiques
- 🏗️ **100% Infrastructure as Code** : Vagrant + Ansible
- 🐳 **Isolation Docker** : Chaque challenge dans son container
- 🔄 **CI/CD Automatisé** : Pipeline GitLab intégré
- 📊 **Monitoring** : Prometheus + Grafana
- 🔐 **Sécurisé** : Isolation réseau, secrets management

### 🛠️ Stack Technique
| Composant     | Technologie          |
|---------------|----------------------|
| Provisioning  | Vagrant + VirtualBox |
| Configuration | Ansible              |
| Runtime       | Docker + Compose     |
| CTF Platform  | CTFd + Whale plugin  |
| CI/CD         | GitLab CE            |
| Monitoring    | Prometheus + Grafana |

## 🚀 Quick Start
```bash
# Clone le repo
git clone https://github.com/USERNAME/ctf-platform-iaac.git
cd ctf-platform-iaac

# Configure l'environnement
cp .env.example .env
# Édite .env avec tes valeurs

# Lance la VM
vagrant up

# Attends 10-15 min, puis accède à :
# CTFd: http://192.168.56.10
# GitLab: http://192.168.56.10:8080
# Grafana: http://192.168.56.10:3000
```

## 🧭 Ce qui marche aujourd'hui

- `vagrant up` lance la VM et le provisioning.
- CTFd est accessible depuis l'hote sur `http://localhost:8000` ou `http://192.168.56.10`.
- La page `/setup` permet de creer le premier compte admin CTFd.
- Les challenges se preparent a partir de `challenges/_template/`.

## 🛠️ Ajouter un challenge

Le dossier [challenges/_template](challenges/_template) est le squelette commun de tous les challenges. Il ne doit pas etre deploie tel quel: il doit etre copie puis specialise.

Pour un challenge de test sur Windows:

```powershell
Set-Location "C:/Users/Ozen/Documents/ctf-platform-iaac-main/ctf-platform-iaac-main"
./scripts/new-challenge.ps1 -Name web-01-test
./scripts/validate-challenge.ps1 -Path challenges/web-01-test
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

Pour Linux/macOS:

```bash
bash ./scripts/new-challenge.sh web-01-test
bash ./scripts/validate-challenge.sh challenges/web-01-test
vagrant ssh -c "cd /vagrant/challenges/web-01-test && docker compose up -d --build"
```

Guide detaille: [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md)

## 🔐 Secrets et niveau de securite

- `.env` doit rester local et ne jamais etre commit.
- `ansible/vars/main.yml` contient encore des valeurs de developpement.
- Pour passer un cap en securite, la prochaine etape est Ansible Vault pour les secrets sensibles.
- Pour un projet de demo/soutenance, le niveau actuel est acceptable. Pour de la prod, il faut durcir.

## 🚧 Suite logique du projet

1. Brancher une vraie gestion des challenges par equipe/joueur avec instance Docker dediee et timer.
2. Ajouter une couche de validation/CI pour bloquer les challenges invalides.
3. Etendre le template vers plusieurs familles: web, osint, sandbox, reverse, pwn.

## 📚 Documentation utile

- [docs/WORKFLOW_PRIORITES.md](docs/WORKFLOW_PRIORITES.md)
- [docs/README_CHALLENGES.md](docs/README_CHALLENGES.md)