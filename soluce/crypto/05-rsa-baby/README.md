# Writeup — rsa-baby

**Catégorie** : Crypto  
**Difficulté** : Hard  
**Points** : 250  
**Flag** : `CTF{rsa_small_n_factored}`

## Concept

RSA repose sur la difficulté de factoriser un grand entier n = p × q. Avec un n petit (ici n = 3233), la factorisation est triviale, et on peut retrouver la clé privée d. Ce challenge illustre pourquoi les clés RSA modernes font au minimum 2048 bits.

**Rappel RSA :**
- Clé publique : (n, e)
- φ(n) = (p-1)(q-1)
- Clé privée : d = e⁻¹ mod φ(n)
- Déchiffrement : m = c^d mod n

## Résolution

### Méthode 1 : À la main
1. Factoriser n = 3233 → 3233 = 61 × 53
2. Calculer φ(n) = (61-1)(53-1) = 60 × 52 = 3120
3. Trouver d tel que 17 × d ≡ 1 mod 3120 → d = 2753
4. Déchiffrer : m = 2557^2753 mod 3233 = 42
5. Le flag est directement fourni : `CTF{rsa_small_n_factored}`

### Méthode 2 : Script Python complet
```python
from math import gcd

def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x, y = extended_gcd(b, a % b)
    return g, y, x - (a // b) * y

def mod_inverse(e, phi):
    g, x, _ = extended_gcd(e, phi)
    if g != 1:
        raise ValueError("L'inverse modulaire n'existe pas")
    return x % phi

# Paramètres publics
n = 3233
e = 17
c = 2557

# Étape 1 : factoriser n (facile car n est petit)
p, q = None, None
for i in range(2, int(n**0.5) + 1):
    if n % i == 0:
        p = i
        q = n // i
        break
print(f"Facteurs : p = {p}, q = {q}")  # p = 53, q = 61

# Étape 2 : calculer phi(n)
phi = (p - 1) * (q - 1)
print(f"φ(n) = {phi}")  # 3120

# Étape 3 : calculer la clé privée d
d = mod_inverse(e, phi)
print(f"Clé privée d = {d}")  # 2753

# Étape 4 : déchiffrer
m = pow(c, d, n)
print(f"Message déchiffré : m = {m}")  # 42

print(f"\nFlag : CTF{{rsa_small_n_factored}}")
```

### Méthode 3 : Vérification de bout en bout
```python
# Vérifier que le chiffrement/déchiffrement est cohérent
p, q, e = 61, 53, 17
n = p * q          # 3233
phi = (p-1)*(q-1)  # 3120
d = 2753           # inverse modulaire de 17 mod 3120

# Chiffrement de m=42
m = 42
c = pow(m, e, n)
print(f"c = {c}")  # 2557

# Déchiffrement
m_dec = pow(c, d, n)
print(f"m déchiffré = {m_dec}")  # 42

# Vérification : e * d ≡ 1 mod phi
print(f"17 * 2753 mod 3120 = {(17 * 2753) % 3120}")  # 1
```

## Correction

En production, utiliser des clés RSA d'au moins 2048 bits (4096 recommandé pour une sécurité à long terme). Pour de la cryptographie asymétrique moderne, préférer les courbes elliptiques (ECDSA, X25519) qui offrent une sécurité équivalente avec des clés bien plus courtes. Ne jamais implémenter RSA soi-même : utiliser une bibliothèque éprouvée (cryptography, openssl).
