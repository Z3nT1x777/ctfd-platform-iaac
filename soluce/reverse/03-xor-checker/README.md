# Soluce — 03-xor-checker

## Contexte

Un binaire Linux applique un XOR octet par octet avec un masque de 4 bytes répété (clé XOR) avant de comparer l'entrée à un tableau de bytes attendus. Le XOR est sa propre opération inverse.

## Étapes de résolution

### Méthode 1 — Ghidra (décompilation)

1. Ouvrir `xor_checker` dans Ghidra et analyser
2. Trouver la fonction `verify()` (ou la logique dans `main`)
3. Identifier deux tableaux :
   - `mask[]` = `{0x42, 0x4c, 0x55, 0x45}` → ASCII = `BLUE`
   - `expected[]` = les bytes chiffrés
4. Appliquer l'opération inverse :

```python
mask = [0x42, 0x4c, 0x55, 0x45]
expected = [
    0x01, 0x18, 0x13, 0x3e,
    0x3a, 0x23, 0x27, 0x1a,
    0x30, 0x29, 0x25, 0x20,
    0x23, 0x38, 0x3c, 0x2b,
    0x25, 0x13, 0x3e, 0x20,
    0x3b, 0x13, 0x22, 0x20,
    0x23, 0x27, 0x28
]
flag = ''.join(chr(b ^ mask[i % 4]) for i, b in enumerate(expected))
print(flag)
# CTF{xor_repeating_key_weak}
```

### Méthode 2 — ltrace

```bash
ltrace ./xor_checker
# Entrer n'importe quoi
# ltrace ne montre pas strcmp ici car la comparaison est manuelle (boucle)
# Préférer gdb pour ce cas
```

### Méthode 3 — gdb (breakpoint sur la boucle de vérification)

```bash
gdb ./xor_checker
disas verify      # ou disas main
# Repérer la boucle XOR + comparaison
# Poser un breakpoint juste après le XOR pour lire le byte attendu
break *0x<adresse_cmp>
run
# Entrer une longue chaîne de 'A'
# Observer les registres : eax = byte XOR-é de l'input, al compare avec le byte expected
```

### Méthode 4 — radare2

```bash
r2 -A ./xor_checker
s sym.verify
pdf
# Identifier le tableau mask (4 bytes) et le tableau expected (27 bytes)
# Extraire via :
px 4 @ 0x<adresse_mask>
px 27 @ 0x<adresse_expected>
```

### Méthode 5 — strings + logique

```bash
strings ./xor_checker
# "BLUE" apparaît comme chaîne (le masque XOR)
# Chercher aussi le tableau expected dans .rodata
```

## Reconstruction du flag

```python
mask = b"BLUE"  # 0x42 0x4C 0x55 0x45
expected = bytes([
    0x01, 0x18, 0x13, 0x3e,
    0x3a, 0x23, 0x27, 0x1a,
    0x30, 0x29, 0x25, 0x20,
    0x23, 0x38, 0x3c, 0x2b,
    0x25, 0x13, 0x3e, 0x20,
    0x3b, 0x13, 0x22, 0x20,
    0x23, 0x27, 0x28
])
flag = bytes(b ^ mask[i % 4] for i, b in enumerate(expected))
print(flag.decode())  # CTF{xor_repeating_key_weak}
```

## Correction

Le masque `BLUE` (`0x42 0x4C 0x55 0x45`) XOR-é avec le tableau `expected[]` donne directement le flag.

**Flag : `CTF{xor_repeating_key_weak}`**
