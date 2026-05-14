#!/usr/bin/env python3
"""Generates a pcap with DNS exfiltration — flag chunks in query names."""
import os, base64
from scapy.all import Ether, IP, UDP, DNS, DNSQR, DNSRR, wrpcap

FLAG    = os.environ.get("FLAG", "CTF{dns_tunnel_data_exfil}")
OUT     = "/data/dns_traffic.pcap"
os.makedirs("/data", exist_ok=True)

CLIENT  = "10.0.1.55"
DNS_SRV = "10.0.1.1"

# Encode flag in base32, split into 8-char chunks
encoded = base64.b32encode(FLAG.encode()).decode().lower().rstrip("=")
chunks  = [encoded[i:i+8] for i in range(0, len(encoded), 8)]

pkts = []
qid  = 1000

# --- Decoy normal DNS (A records) ---
decoys = ["google.com", "github.com", "api.internal.corp", "update.microsoft.com"]
for d in decoys:
    qid += 1
    q = (Ether() /
         IP(src=CLIENT, dst=DNS_SRV) /
         UDP(sport=12000+qid, dport=53) /
         DNS(id=qid, rd=1, qd=DNSQR(qname=d)))
    r = (Ether() /
         IP(src=DNS_SRV, dst=CLIENT) /
         UDP(sport=53, dport=12000+qid) /
         DNS(id=qid, qr=1, aa=1, qd=DNSQR(qname=d),
             an=DNSRR(rrname=d, type="A", rdata="1.1.1.1", ttl=60)))
    pkts += [q, r]

# --- Exfiltration: flag chunks as subdomains ---
for i, chunk in enumerate(chunks):
    qid += 1
    qname = f"{chunk}.exfil.ctf.local"
    q = (Ether() /
         IP(src=CLIENT, dst=DNS_SRV) /
         UDP(sport=13000+qid, dport=53) /
         DNS(id=qid, rd=1, qd=DNSQR(qname=qname)))
    r = (Ether() /
         IP(src=DNS_SRV, dst=CLIENT) /
         UDP(sport=53, dport=13000+qid) /
         DNS(id=qid, qr=1, aa=0, rcode=3,  # NXDOMAIN — exfil server doesn't resolve
             qd=DNSQR(qname=qname)))
    pkts += [q, r]

# --- More decoy after ---
for d in ["time.windows.com", "ocsp.digicert.com"]:
    qid += 1
    q = (Ether() /
         IP(src=CLIENT, dst=DNS_SRV) /
         UDP(sport=14000+qid, dport=53) /
         DNS(id=qid, rd=1, qd=DNSQR(qname=d)))
    pkts.append(q)

wrpcap(OUT, pkts)
print(f"[+] {len(pkts)} packets, {len(chunks)} exfil chunks → {OUT}")
print(f"[+] Encoded: {encoded}")
print(f"[+] Chunks:  {chunks}")
