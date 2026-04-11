# Linux Capabilities

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Hard  
**Points** : 400

## Description

Ce serveur ne présente aucun binaire SUID évident. Pourtant, une élévation de privilèges est possible.
Les Linux capabilities permettent d'accorder des privilèges granulaires à des processus sans SUID.
Trouve quel binaire dispose d'une capability dangereuse et exploite-la.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5024
# password: player2026
```

## Objectif

Lire le contenu de `/root/flag.txt` en escaladant les privilèges depuis l'utilisateur `player`.
