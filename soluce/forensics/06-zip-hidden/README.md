# Soluce — 06-zip-hidden

## Contexte

Une archive ZIP contient plusieurs fichiers leurres. Le flag est caché dans le commentaire de l'archive ZIP (champ `z.comment` du format ZIP).

## Étapes de résolution

### Méthode 1 — unzip -v (liste avec commentaires)

```bash
# Afficher les métadonnées incluant le commentaire
unzip -v archive.zip

# Ou lire spécifiquement le commentaire
unzip -z archive.zip
```

### Méthode 2 — zipinfo

```bash
zipinfo archive.zip
```

### Méthode 3 — strings

```bash
# Le commentaire est stocké en clair à la fin du fichier ZIP
strings archive.zip | tail -20

# Chercher le pattern CTF
strings archive.zip | grep "CTF{"
```

### Méthode 4 — Python (zipfile)

```python
import zipfile

with zipfile.ZipFile("archive.zip") as z:
    # Commentaire global de l'archive
    print("Archive comment:", z.comment.decode())

    # Commentaires par fichier
    for info in z.infolist():
        if info.comment:
            print(f"{info.filename} comment:", info.comment.decode())
```

### Méthode 5 — hexdump / xxd

```bash
# Le commentaire de fin d'archive est dans l'End of Central Directory Record
# Chercher la signature EOCD : 50 4b 05 06
xxd archive.zip | grep -A 5 "504b 0506"
```

### Méthode 6 — binwalk

```bash
binwalk archive.zip
binwalk -e archive.zip
```

## Correction

L'archive contient 4 fichiers leurres (`readme.txt`, `notes.txt`, `data.csv`, `image.jpg`) avec du contenu aléatoire. Le flag est dans le commentaire global de l'archive :

```python
import zipfile
with zipfile.ZipFile("archive.zip") as z:
    print(z.comment.decode())
# CTF{zip_comment_forensics}
```

```bash
unzip -z archive.zip
# Archive:  archive.zip
# CTF{zip_comment_forensics}
```

**Flag : `CTF{zip_comment_forensics}`**
