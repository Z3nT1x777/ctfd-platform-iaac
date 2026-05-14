#!/usr/bin/env python3
"""Generates a PNG with the flag hidden in LSB of the red channel."""
import os, random
from PIL import Image

FLAG = os.environ.get("FLAG", "CTF{lsb_pixels_dont_lie}") + "\x00"
OUT  = "/data/landscape.png"
os.makedirs("/data", exist_ok=True)

WIDTH, HEIGHT = 512, 512
rng = random.Random(1337)

# --- Create a convincing gradient landscape ---
img = Image.new("RGB", (WIDTH, HEIGHT))
pixels = []
for y in range(HEIGHT):
    for x in range(WIDTH):
        # Sky gradient (top half)
        if y < HEIGHT // 2:
            r = int(135 + (y / (HEIGHT // 2)) * 50)
            g = int(180 + (y / (HEIGHT // 2)) * 30)
            b = int(230 - (y / (HEIGHT // 2)) * 30)
        else:
            # Ground (bottom half) with noise
            r = int(80 + rng.gauss(0, 8))
            g = int(120 + rng.gauss(0, 6))
            b = int(60 + rng.gauss(0, 5))
        # Clamp
        r = max(0, min(255, r + rng.randint(-3, 3)))
        g = max(0, min(255, g + rng.randint(-3, 3)))
        b = max(0, min(255, b + rng.randint(-3, 3)))
        pixels.append((r, g, b))

# --- Embed flag in LSB of red channel ---
flag_bits = "".join(format(ord(c), "08b") for c in FLAG)
for i, bit in enumerate(flag_bits):
    r, g, b = pixels[i]
    r = (r & 0xFE) | int(bit)
    pixels[i] = (r, g, b)

img.putdata(pixels)
img.save(OUT, "PNG")
print(f"[+] Image generated → {OUT} ({len(flag_bits)} bits embedded, {len(FLAG)} chars)")
