# Soluce — 05-strings-dump

## Contexte

Un dump mémoire (fichier texte simulant un memdump) contient des milliers de lignes de données. Le flag est caché au milieu, entouré de bruit.

## Étapes de résolution

### Méthode 1 — strings + grep (la plus rapide)

```bash
# Chercher directement le pattern CTF{
strings memdump.bin | grep "CTF{"

# Ou si c'est un fichier texte
grep "CTF{" memdump.bin
```

### Méthode 2 — grep avec contexte

```bash
# Afficher la ligne + 2 lignes de contexte
grep -n "CTF{" memdump.bin -A 2 -B 2
```

### Méthode 3 — foremost / binwalk

```bash
# Analyse forensique du fichier binaire
binwalk memdump.bin
foremost -i memdump.bin -o output/
```

### Méthode 4 — Python

```python
with open("memdump.bin", errors='ignore') as f:
    for i, line in enumerate(f, 1):
        if 'CTF{' in line:
            print(f"Ligne {i}: {line.strip()}")
```

### Méthode 5 — Volatility (pour de vrais memdumps)

Pour les vrais dumps mémoire (non simulés) :
```bash
vol.py -f memdump.bin --profile=Win7SP1x64 yarascan -Y "CTF{"
vol.py -f memdump.bin --profile=Win7SP1x64 dumpfiles
```

## Correction

Le flag apparaît vers la ligne 1800 du dump, au milieu d'autres chaînes ASCII :

```
...
4a:f8:32:e1:00:00:00:00
CTF{strings_memdump_analysis}
3f:21:00:00:00:08:33:f7
...
```

La commande `strings memdump.bin | grep "CTF{"` le retrouve immédiatement.

**Flag : `CTF{strings_memdump_analysis}`**
