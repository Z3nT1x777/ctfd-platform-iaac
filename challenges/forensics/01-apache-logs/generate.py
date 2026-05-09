#!/usr/bin/env python3
"""Generates a fake Apache access log with an exfiltrated flag hidden inside."""
import random, base64, os
from datetime import datetime, timedelta

FLAG = os.environ.get("FLAG", "CTF{apache_log_never_lies}")
OUT  = "/data/access.log"
os.makedirs("/data", exist_ok=True)

AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/115.0",
    "curl/7.88.1",
    "python-requests/2.28.0",
]
PATHS = ["/", "/index.html", "/login", "/dashboard", "/api/status",
         "/static/main.css", "/static/app.js", "/favicon.ico",
         "/robots.txt", "/api/users", "/api/health"]

rng  = random.Random(42)
base = datetime(2026, 4, 15, 2, 0, 0)
lines = []

def rand_ip(internal=True):
    if internal:
        return f"10.0.1.{rng.randint(2,50)}"
    return f"{rng.randint(80,220)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"

def fmt_time(dt):
    return dt.strftime("%d/%b/%Y:%H:%M:%S +0000")

# Normal traffic — 420 lines
for i in range(420):
    ts   = base + timedelta(seconds=i * 5 + rng.randint(0, 4))
    ip   = rand_ip(rng.random() > 0.1)
    path = rng.choice(PATHS)
    code = rng.choices([200, 200, 200, 304, 404, 403], weights=[60,20,10,5,3,2])[0]
    size = rng.randint(200, 12000) if code == 200 else rng.randint(0, 300)
    ua   = rng.choice(AGENTS)
    meth = "GET"
    lines.append(f'{ip} - - [{fmt_time(ts)}] "{meth} {path} HTTP/1.1" {code} {size} "-" "{ua}"')

# === Exfiltration request hidden at position ~230 ===
exfil_ts  = base + timedelta(seconds=230 * 5 + 2)
exfil_ip  = "185.220.101.47"   # known Tor exit node range
b64_flag  = base64.b64encode(FLAG.encode()).decode()
exfil_line = (
    f'{exfil_ip} - - [{fmt_time(exfil_ts)}] '
    f'"POST /api/export?data={b64_flag}&fmt=json HTTP/1.1" '
    f'200 23 "http://10.0.1.5/dashboard" "python-requests/2.31.0"'
)
lines.insert(230, exfil_line)

# Normal traffic — 80 more lines
for i in range(80):
    ts   = base + timedelta(seconds=(420 + i) * 5 + rng.randint(0, 4))
    ip   = rand_ip()
    path = rng.choice(PATHS)
    code = rng.choices([200, 304, 404], weights=[70, 20, 10])[0]
    size = rng.randint(200, 8000)
    ua   = rng.choice(AGENTS)
    lines.append(f'{ip} - - [{fmt_time(ts)}] "GET {path} HTTP/1.1" {code} {size} "-" "{ua}"')

with open(OUT, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f"[+] Generated {len(lines)} log lines → {OUT}")
