# Soluce — 03-stego-lsb

## Contexte

Une image PNG contient un message caché dans le bit de poids faible (LSB — Least Significant Bit) du canal rouge. La stéganographie LSB est une technique classique qui modifie imperceptiblement les pixels.

## Étapes de résolution

### Méthode 1 — zsteg (outil dédié)

```bash
# Installer zsteg (Ruby)
gem install zsteg

# Analyser l'image
zsteg image.png

# L'output montrera les données cachées dans les LSB
```

### Méthode 2 — stegsolve / Aperi'Solve

Aller sur [https://www.aperisolve.com](https://www.aperisolve.com) et uploader l'image. L'outil analyse automatiquement les plans LSB et affiche les données cachées.

### Méthode 3 — Python (Pillow)

```python
from PIL import Image

def extract_lsb(path):
    img = Image.open(path).convert('RGB')
    pixels = list(img.getdata())
    bits = []
    for r, g, b in pixels:
        bits.append(r & 1)  # LSB du canal rouge

    # Regrouper en octets
    chars = []
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        if len(byte_bits) < 8:
            break
        val = int(''.join(str(b) for b in byte_bits), 2)
        if val == 0:
            break  # null terminator
        chars.append(chr(val))

    return ''.join(chars)

print(extract_lsb("image.png"))
```

### Méthode 4 — binwalk

```bash
# binwalk peut détecter des données cachées dans les images
binwalk image.png
binwalk -e image.png  # extrait les données trouvées
```

## Correction

Le flag est encodé bit par bit dans le LSB du canal rouge des pixels, lu de gauche à droite, haut en bas. Le script Python ci-dessus l'extrait directement.

**Flag : `CTF{lsb_pixels_dont_lie}`**
