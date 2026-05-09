#!/usr/bin/env python3
"""Generates a fake memory dump strings file with the flag hidden inside."""
import os, random, string

FLAG = os.environ.get("FLAG", "CTF{strings_memdump_analysis}")
OUT  = "/data/memdump.strings"
os.makedirs("/data", exist_ok=True)

rng = random.Random(9001)

WORDS = [
    "kernel32.dll", "ntdll.dll", "LoadLibraryA", "GetProcAddress",
    "VirtualAlloc", "CreateThread", "WriteProcessMemory", "NtQuerySystemInformation",
    "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
    "C:\\Windows\\System32\\svchost.exe", "cmd.exe /c whoami",
    "SeDebugPrivilege", "TOKEN_ALL_ACCESS", "OpenProcessToken",
    "127.0.0.1", "192.168.1.1", "0.0.0.0:4444", "CONNECT",
    "Mozilla/5.0 (Windows NT 10.0)", "User-Agent:", "Content-Type:",
    "application/json", "Authorization: Bearer", "HTTP/1.1 200 OK",
    "password", "admin", "login", "session", "token",
    "AES-256-CBC", "RSA-2048", "SHA-256", "HMAC",
    "malloc", "free", "memcpy", "strncpy", "sprintf",
]

def rand_str(min_len=4, max_len=40):
    charset = string.ascii_letters + string.digits + " ._-/:\\@"
    length  = rng.randint(min_len, max_len)
    return "".join(rng.choices(charset, k=length))

lines = []

# 1800 lines before flag
for _ in range(1800):
    if rng.random() < 0.15:
        lines.append(rng.choice(WORDS))
    else:
        lines.append(rand_str())

# --- Flag hidden at a random position around 1800-2200 ---
flag_pos = rng.randint(1800, 2200)
lines.append(FLAG)  # will be inserted at flag_pos below

# 1800 lines after
for _ in range(1800):
    if rng.random() < 0.15:
        lines.append(rng.choice(WORDS))
    else:
        lines.append(rand_str())

# Insert flag at the correct position
all_lines = lines[:1800] + [FLAG] + lines[1800:]

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(all_lines) + "\n")

print(f"[+] {len(all_lines)} lines, flag at line ~{1800} → {OUT}")
