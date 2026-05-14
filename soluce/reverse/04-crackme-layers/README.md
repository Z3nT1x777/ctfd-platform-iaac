# Soluce — 04-crackme-layers

## Contexte

Un crackme Python applique trois transformations à l'entrée avant de la comparer à une cible. Les transformations sont empilées (composées), et il faut les appliquer dans l'ordre inverse pour retrouver le flag.

## Transformations

```
input → layer1 (base64 encode) → layer2 (XOR 0x0F) → layer3 (reverse) → TARGET
```

Pour retrouver le flag : appliquer l'inverse de chaque couche, dans l'ordre inverse.

```
TARGET → inv_layer3 (reverse) → inv_layer2 (XOR 0x0F) → inv_layer1 (base64 decode) → flag
```

## Étapes de résolution

### Étape 1 — Analyser les couches

```python
def layer1(s): return base64.b64encode(s.encode()).decode()   # encode en base64
def layer2(s): return ''.join(chr(ord(c)^0x0F) for c in s)   # XOR chaque char
def layer3(s): return s[::-1]                                  # inverse la chaîne
```

Notes :
- `layer3` est son propre inverse (double reverse = identité)
- `layer2` est son propre inverse (XOR est involutif : `x ^ k ^ k = x`)
- `layer1` inverse = `base64.b64decode`

### Étape 2 — Inverser les couches

```python
import base64

TARGET = "6]XU|YXUx6>lvYXjgw=WcYbl`]<jH]>^"

# Inverse layer3 : reverse
s = TARGET[::-1]
print("Après inv_layer3 :", s)
# Q1RGe3RocmVlX2xheWVyc19wZWVsZWR9

# Inverse layer2 : XOR 0x0F (sa propre inverse)
s = ''.join(chr(ord(c) ^ 0x0F) for c in s)
print("Après inv_layer2 :", s)
# Q1RGe3RocmVlX2xheWVyc19wZWVsZWR9  ← base64

# Inverse layer1 : base64 decode
flag = base64.b64decode(s).decode()
print("Flag :", flag)
# CTF{three_layers_peeled}
```

### Script complet (one-liner)

```python
import base64
TARGET = "6]XU|YXUx6>lvYXjgw=WcYbl`]<jH]>^"
s = TARGET[::-1]
s = ''.join(chr(ord(c)^0x0F) for c in s)
print(base64.b64decode(s).decode())
```

### Vérification

```python
import base64

def layer1(s): return base64.b64encode(s.encode()).decode()
def layer2(s): return ''.join(chr(ord(c)^0x0F) for c in s)
def layer3(s): return s[::-1]

flag = "CTF{three_layers_peeled}"
assert layer3(layer2(layer1(flag))) == "6]XU|YXUx6>lvYXjgw=WcYbl`]<jH]>^"
print("OK !")
```

## Correction

En appliquant les 3 inverses dans l'ordre inverse :

```
TARGET[::-1]           → base64 string
XOR 0x0F               → base64 string (inchangé car XOR est involutif)
base64.b64decode(...)  → CTF{three_layers_peeled}
```

**Flag : `CTF{three_layers_peeled}`**
