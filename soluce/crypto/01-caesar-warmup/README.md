# Writeup — caesar-warmup

**Catégorie** : Crypto  
**Difficulté** : Easy  
**Points** : 50  
**Flag** : `CTF{julius_caesar_strikes_again}`

## Concept

Le chiffrement de César est l'une des plus anciennes techniques de cryptographie par substitution. Chaque lettre du texte clair est remplacée par une lettre décalée d'un nombre fixe de positions dans l'alphabet. ROT13 est le cas particulier où le décalage est de 13 — ce qui est auto-inverse (appliquer ROT13 deux fois redonne le texte original).

## Résolution

### Méthode 1 : Outil en ligne
1. Ouvrir [CyberChef](https://gchq.github.io/CyberChef/) ou [dcode.fr/chiffre-rot-13](https://www.dcode.fr/chiffre-rot-13)
2. Coller le ciphertext : `PGS{whyvhf_pnrfne_fgevxrf_ntnva}`
3. Appliquer ROT13
4. Résultat : `CTF{julius_caesar_strikes_again}`

### Méthode 2 : Script Python
```python
ciphertext = "PGS{whyvhf_pnrfne_fgevxrf_ntnva}"

def rot13_decrypt(text):
    result = []
    for c in text:
        if c.isupper():
            result.append(chr((ord(c) - 65 + 13) % 26 + 65))
        elif c.islower():
            result.append(chr((ord(c) - 97 + 13) % 26 + 97))
        else:
            result.append(c)
    return ''.join(result)

print(rot13_decrypt(ciphertext))
# CTF{julius_caesar_strikes_again}
```

### Méthode 3 : Python one-liner
```python
import codecs
print(codecs.decode("PGS{whyvhf_pnrfne_fgevxrf_ntnva}", "rot_13"))
```

## Correction

En production, ne jamais utiliser le chiffrement de César ou ROT13 pour protéger des données sensibles. Ces algorithmes sont trivialmente cassables par force brute (26 décalages possibles) ou par analyse de fréquences. Pour du chiffrement réel, utiliser AES-256-GCM ou ChaCha20-Poly1305.
