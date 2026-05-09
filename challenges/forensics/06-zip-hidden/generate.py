#!/usr/bin/env python3
"""Generates a ZIP with the flag hidden in the archive comment."""
import os, zipfile, random, string

FLAG = os.environ.get("FLAG", "CTF{zip_comment_forensics}")
OUT  = "/data/evidence.zip"
os.makedirs("/data", exist_ok=True)

rng = random.Random(2026)

def lorem(n=50):
    words = ["le", "la", "les", "un", "une", "des", "et", "ou", "mais", "donc",
             "projet", "rapport", "client", "réunion", "document", "analyse",
             "équipe", "résultat", "données", "système", "version", "fichier"]
    return " ".join(rng.choices(words, k=n)).capitalize() + "."

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    # Decoy files
    z.writestr("rapport_avril_2026.txt",
               f"Rapport mensuel — Avril 2026\n\n{lorem(80)}\n\n{lorem(60)}\n\nRédacteur : Alice Martin")
    z.writestr("contacts.csv",
               "nom,email,telephone\nAlice Martin,alice@corp.fr,+33600000001\n"
               "Bob Dupont,bob@corp.fr,+33600000002\nCharlie Petit,charlie@corp.fr,+33600000003")
    z.writestr("notes_reunion.txt",
               f"Notes réunion 14/04/2026\n\nParticipants : Alice, Bob, Charlie\n\n{lorem(40)}\n\nActions :\n- {lorem(15)}\n- {lorem(12)}")
    z.writestr("TODO.txt", "- Finaliser le rapport Q1\n- Envoyer les accès à Charlie\n- Backup serveur vendredi")
    # Hide flag in archive comment
    z.comment = FLAG.encode()

print(f"[+] ZIP created → {OUT}")
print(f"[+] Comment: {FLAG}")
