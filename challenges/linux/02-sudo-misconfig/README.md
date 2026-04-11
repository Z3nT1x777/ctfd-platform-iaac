# Sudo Misconfiguration

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Easy  
**Points** : 150

## Description

Un administrateur distrait a configuré sudo de manière trop permissive sur ce serveur.
Identifie quelle commande tu peux exécuter en tant que root et utilise-la pour t'échapper vers un shell privilégié.
Le flag se trouve dans `/root/flag.txt`.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5021
# password: player2026
```

## Objectif

Lire le contenu de `/root/flag.txt` en escaladant les privilèges depuis l'utilisateur `player`.
