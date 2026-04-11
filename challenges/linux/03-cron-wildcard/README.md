# Cron Wildcard Injection

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Medium  
**Points** : 250

## Description

Un job cron tourne en arrière-plan sur ce serveur et effectue des sauvegardes régulières.
Le script utilise un wildcard dans un répertoire accessible en écriture — une combinaison dangereuse.
Exploite cette configuration pour exécuter du code arbitraire en tant que root.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5022
# password: player2026
```

## Objectif

Lire le contenu de `/root/flag.txt` en escaladant les privilèges depuis l'utilisateur `player`.
