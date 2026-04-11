# SUID Classic

**Catégorie** : Linux / Privilege Escalation  
**Difficulté** : Easy  
**Points** : 100

## Description

Un serveur Linux expose un binaire standard avec des droits inhabituels.
Explore le système, trouve le fichier avec des permissions spéciales et escalade tes privilèges jusqu'à root.
Le flag se trouve dans `/root/flag.txt`.

## Connexion

```bash
ssh player@<TARGET_IP> -p 5020
# password: player2026
```

## Objectif

Lire le contenu de `/root/flag.txt` en escaladant les privilèges depuis l'utilisateur `player`.
