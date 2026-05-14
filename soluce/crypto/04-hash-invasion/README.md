# Writeup — hash-invasion

**Catégorie** : Crypto  
**Difficulté** : Easy  
**Points** : 150  
**Flag** : `CTF{sunshine}`

## Concept

MD5 est une fonction de hachage cryptographique : elle transforme des données en un condensé de 128 bits (32 caractères hexadécimaux) de manière déterministe et non réversible. Cependant, pour les mots de passe courants, des bases de données précalculées (rainbow tables) permettent de retrouver le plaintext à partir du hash en quelques secondes.

## Résolution

### Méthode 1 : Rainbow table en ligne
1. Aller sur [crackstation.net](https://crackstation.net/)
2. Coller le hash : `0571749e2ac330a7455809c6b0e7af90`
3. Résultat : `sunshine`
4. Flag : `CTF{sunshine}`

### Méthode 2 : cmd5.org ou hashes.com
1. Aller sur [hashes.com/en/decrypt/hash](https://hashes.com/en/decrypt/hash)
2. Soumettre le hash MD5
3. Obtenir `sunshine`

### Méthode 3 : Vérification Python
```python
import hashlib

# Vérifier que 'sunshine' produit bien le hash donné
mot = "sunshine"
hash_calcule = hashlib.md5(mot.encode()).hexdigest()
print(hash_calcule)
# 0571749e2ac330a7455809c6b0e7af90

# Brute force par dictionnaire (si rainbow table non disponible)
dictionnaire = ["password", "123456", "sunshine", "letmein", "admin", "welcome"]
hash_cible = "0571749e2ac330a7455809c6b0e7af90"

for mot in dictionnaire:
    if hashlib.md5(mot.encode()).hexdigest() == hash_cible:
        print(f"Mot de passe trouvé : {mot}")
        print(f"Flag : CTF{{{mot}}}")
        break
```

### Méthode 4 : hashcat (attaque par dictionnaire)
```bash
echo "0571749e2ac330a7455809c6b0e7af90" > hash.txt
hashcat -m 0 -a 0 hash.txt /usr/share/wordlists/rockyou.txt
```

## Correction

En production, ne jamais stocker des mots de passe avec MD5 (même avec salt, MD5 est trop rapide). Utiliser bcrypt, scrypt ou Argon2 — ces algorithmes sont intentionnellement lents et résistants aux attaques par GPU. MD5 peut calculer des milliards de hashes par seconde sur une carte graphique moderne.
