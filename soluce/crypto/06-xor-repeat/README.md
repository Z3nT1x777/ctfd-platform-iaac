# Writeup — xor-repeat

**Catégorie** : Crypto  
**Difficulté** : Hard  
**Points** : 300  
**Flag** : `CTF{xor_repeating_key_weak}`

## Concept

Le XOR à clé répétée (aussi appelé chiffre de Vernam dégradé ou chiffre de Vigenère binaire) XOR chaque octet du message avec l'octet correspondant de la clé, répétée cycliquement. Si la clé est courte et que le plaintext a une structure connue (comme un flag commençant par `CTF{`), on peut retrouver la clé par attaque à texte clair connu (known-plaintext attack).

**Propriété fondamentale du XOR :**
- Si `cipher = plain XOR key`
- Alors `key = cipher XOR plain`
- Et `plain = cipher XOR key`

## Résolution

### Méthode 1 : Known-plaintext attack (à la main)

Le flag commence toujours par `CTF{` (4 octets = longueur de la clé) :
```
cipher[0] = 0x01 → key[0] = 0x01 XOR 0x43 ('C') = 0x42 ('B')
cipher[1] = 0x18 → key[1] = 0x18 XOR 0x54 ('T') = 0x4C ('L')
cipher[2] = 0x13 → key[2] = 0x13 XOR 0x46 ('F') = 0x55 ('U')
cipher[3] = 0x3e → key[3] = 0x3e XOR 0x7B ('{') = 0x45 ('E')
```
Clé retrouvée : `BLUE`

### Méthode 2 : Script Python complet
```python
# Ciphertext en hex
cipher_hex = "01 18 13 3e 3a 23 27 1a 30 29 25 20 23 38 3c 2b 25 13 3e 20 3b 13 22 20 23 27 28"
cipher = bytes.fromhex(cipher_hex.replace(" ", ""))

# Known-plaintext : on sait que le flag commence par "CTF{"
known = b"CTF{"

# Retrouver la clé (longueur 4)
key = bytes(cipher[i] ^ known[i] for i in range(4))
print(f"Clé trouvée : {key}")  # b'BLUE'

# Déchiffrer le message complet
plaintext = bytes(cipher[i] ^ key[i % len(key)] for i in range(len(cipher)))
print(f"Flag : {plaintext.decode()}")
# CTF{xor_repeating_key_weak}
```

### Méthode 3 : Vérification du chiffrement original
```python
# Comment le ciphertext a été généré
flag = b"CTF{xor_repeating_key_weak}"
key = b"BLUE"
cipher = bytes(flag[i] ^ key[i % len(key)] for i in range(len(flag)))
print(cipher.hex())
# 011813 3e3a23271a30292520233 83c2b25133e203b13222023 2728

# Déchiffrement (XOR est son propre inverse)
decrypted = bytes(cipher[i] ^ key[i % len(key)] for i in range(len(cipher)))
print(decrypted.decode())
# CTF{xor_repeating_key_weak}
```

### Méthode 4 : CyberChef
1. Ouvrir [CyberChef](https://gchq.github.io/CyberChef/)
2. Input : `01 18 13 3e 3a 23 27 1a 30 29 25 20 23 38 3c 2b 25 13 3e 20 3b 13 22 20 23 27 28`
3. Ajouter l'opération **From Hex**
4. Ajouter l'opération **XOR** avec la clé `BLUE` (UTF-8) en mode Standard
5. Résultat : `CTF{xor_repeating_key_weak}`

## Correction

Le XOR à clé répétée est vulnérable à l'attaque à texte clair connu, à l'analyse statistique (si le message est long), et à la réutilisation de clé (two-time pad). Pour un chiffrement XOR sécurisé, utiliser un pad à usage unique (one-time pad) de même longueur que le message, avec une clé vraiment aléatoire et jamais réutilisée. En pratique, préférer AES-GCM ou ChaCha20-Poly1305.
