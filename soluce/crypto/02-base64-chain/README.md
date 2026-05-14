# Writeup — base64-chain

**Catégorie** : Crypto  
**Difficulté** : Easy  
**Points** : 75  
**Flag** : `CTF{base64_is_not_encryption}`

## Concept

Base64 est un **encodage**, pas un chiffrement. Il transforme des données binaires en texte ASCII en utilisant 64 caractères (`A-Z`, `a-z`, `0-9`, `+`, `/`). Il n'y a pas de clé secrète — n'importe qui peut décoder du base64. Doubler l'encodage n'ajoute aucune sécurité.

## Résolution

### Méthode 1 : CyberChef
1. Ouvrir [CyberChef](https://gchq.github.io/CyberChef/)
2. Coller le ciphertext : `UTFSR2UySmhjMlUyTkY5cGMxOXViM1JmWlc1amNubHdkR2x2Ym4wPQ==`
3. Ajouter l'opération **From Base64** (deux fois)
4. Résultat final : `CTF{base64_is_not_encryption}`

### Méthode 2 : Script Python
```python
import base64

encoded = b"UTFSR2UySmhjMlUyTkY5cGMxOXViM1JmWlc1amNubHdkR2x2Ym4wPQ=="

# Premier décodage
step1 = base64.b64decode(encoded)
print("Après 1er décodage :", step1)
# Q1RGe2Jhc2U2NF9pc19ub3RfZW5jcnlwdGlvbn0=

# Deuxième décodage
step2 = base64.b64decode(step1)
print("Après 2ème décodage :", step2.decode())
# CTF{base64_is_not_encryption}
```

### Méthode 3 : Ligne de commande
```bash
echo "UTFSR2UySmhjMlUyTkY5cGMxOXViM1JmWlc1amNubHdkR2x2Ym4wPQ==" | base64 -d | base64 -d
```

## Correction

Ne jamais confondre encodage et chiffrement. Base64 est destiné au transport de données binaires (emails, URLs, JSON) — pas à la sécurité. Pour protéger un secret, utiliser un vrai chiffrement symétrique (AES) ou asymétrique (RSA/ECC) avec une clé secrète.
