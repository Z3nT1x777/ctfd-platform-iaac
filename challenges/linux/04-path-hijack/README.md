# PATH Hijacking via SUID Binary

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Medium  
**Points** : 300

## Description

Un binaire SUID custom a été déployé sur ce serveur par un développeur inexpérimenté.
Le binaire appelle une commande externe sans spécifier son chemin absolu.
Contrôle l'environnement d'exécution pour rediriger l'appel vers ton propre script.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5023
# password: player2026
```

## Objectif

Lire le contenu de `/root/flag.txt` en escaladant les privilèges depuis l'utilisateur `player`.
