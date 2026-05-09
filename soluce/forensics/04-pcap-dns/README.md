# Soluce — 04-pcap-dns

## Contexte

Un fichier `.pcap` contient du trafic DNS suspect. Des données ont été exfiltrées via les sous-domaines des requêtes DNS — technique appelée "DNS tunneling" ou "DNS exfiltration".

## Étapes de résolution

### Méthode 1 — Wireshark (GUI)

1. Ouvrir le fichier avec Wireshark
2. Filtre : `dns.qry.name contains "exfil"` ou `dns`
3. Observer les noms de domaine : des préfixes inhabituels (lettres majuscules + chiffres) = base32
4. Extraire les sous-domaines et les décoder

### Méthode 2 — tshark + base32

```bash
# Extraire tous les noms DNS interrogés
tshark -r capture.pcap -Y "dns.flags.response==0" -T fields -e dns.qry.name

# Les sous-domaines contiennent du base32 :
# ex: KNQWIZLTOQQGK3TFNZ2CA5DFOJZXI.exfil.local
# Extraire la partie avant .exfil.local et décoder
echo "KNQWIZLTOQQGK3TFNZ2CA5DFOJZXI" | base32 -d 2>/dev/null || \
python3 -c "import base64; print(base64.b32decode('KNQWIZLTOQQGK3TFNZ2CA5DFOJZXI====='))"
```

### Méthode Python complète

```python
from scapy.all import rdpcap, DNSQR
import base64

pkts = rdpcap("capture.pcap")
chunks = {}

for pkt in pkts:
    if pkt.haslayer(DNSQR):
        qname = pkt[DNSQR].qname.decode(errors='ignore').rstrip('.')
        if '.exfil.' in qname:
            parts = qname.split('.')
            # Format: <seq>.<b32data>.exfil.local
            seq = int(parts[0])
            b32_data = parts[1].upper()
            # Padding
            pad = (8 - len(b32_data) % 8) % 8
            b32_data += '=' * pad
            try:
                decoded = base64.b32decode(b32_data).decode()
                chunks[seq] = decoded
            except:
                pass

flag = ''.join(chunks[k] for k in sorted(chunks))
print("Flag:", flag)
```

### Méthode 3 — strings

```bash
strings capture.pcap | grep -oE '[A-Z2-7]{16,}' | while read b32; do
    python3 -c "import base64; print(base64.b32decode('$b32' + '=' * ((8 - len('$b32')%8)%8)))" 2>/dev/null
done | grep CTF
```

## Correction

Les requêtes DNS suivent le schéma `<seq>.<b32chunk>.exfil.ctf.local`. En concaténant les fragments base32 dans l'ordre des séquences et en les décodant :

```
KNQWIZLT → CTF{dns
OQQGK3TF → _tunnel
NZ2CAZDF → _data_e
OJZXI=== → xfil}
```

→ `CTF{dns_tunnel_data_exfil}`

**Flag : `CTF{dns_tunnel_data_exfil}`**
