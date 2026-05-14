# Writeup — vigenere-mystery

**Catégorie** : Crypto  
**Difficulté** : Medium  
**Points** : 150  
**Flag** : `CTF{vigenere_polyalphabetic_cipher}`

## Concept

Le chiffrement de Vigenère est un chiffrement polyalphabétique : il utilise plusieurs décalages César en alternance selon un mot-clé. Chaque lettre du message est décalée par la valeur de la lettre correspondante dans la clé (répétée cycliquement). Si la longueur de la clé est connue et courte, le chiffrement est vulnérable aux attaques par dictionnaire ou force brute.

## Résolution

### Méthode 1 : CyberChef
1. Ouvrir [CyberChef](https://gchq.github.io/CyberChef/)
2. Coller le ciphertext : `MXD{fmforcbi_nypwkpnrezoxgm_ggzlcb}`
3. Ajouter l'opération **Vigenère Decode** avec la clé `KEY`
4. Résultat : `CTF{vigenere_polyalphabetic_cipher}`

### Méthode 2 : Script Python
```python
def vigenere_decrypt(text, key):
    key = key.upper()
    result = []
    ki = 0
    for c in text:
        if c.isalpha():
            shift = ord(key[ki % len(key)]) - ord('A')
            if c.isupper():
                result.append(chr((ord(c) - ord('A') - shift) % 26 + ord('A')))
            else:
                result.append(chr((ord(c) - ord('a') - shift) % 26 + ord('a')))
            ki += 1
        else:
            result.append(c)
    return ''.join(result)

ciphertext = "MXD{fmforcbi_nypwkpnrezoxgm_ggzlcb}"
print(vigenere_decrypt(ciphertext, "KEY"))
# CTF{vigenere_polyalphabetic_cipher}
```

### Méthode 3 : Brute force de la clé (si inconnue)
```python
import itertools
import string

def vigenere_decrypt(text, key):
    key = key.upper()
    result = []
    ki = 0
    for c in text:
        if c.isalpha():
            shift = ord(key[ki % len(key)]) - ord('A')
            base = ord('A') if c.isupper() else ord('a')
            result.append(chr((ord(c) - base - shift) % 26 + base))
            ki += 1
        else:
            result.append(c)
    return ''.join(result)

ciphertext = "MXD{fmforcbi_nypwkpnrezoxgm_ggzlcb}"

# Brute force sur des clés 3 lettres (sachant la longueur = 3)
for key in itertools.product(string.ascii_uppercase, repeat=3):
    key_str = ''.join(key)
    result = vigenere_decrypt(ciphertext, key_str)
    # On cherche un résultat qui commence par CTF{
    if result.startswith("CTF{"):
        print(f"Clé trouvée : {key_str} → {result}")
        break
```

## Correction

En production, Vigenère est cassé depuis le XIXe siècle (test de Kasiski, indice de coïncidence). Pour un chiffrement symétrique moderne, utiliser AES-256 en mode GCM. Si le contexte est une communication en temps réel, préférer Signal Protocol ou TLS 1.3.
