#!/usr/bin/env python3
"""Generates a pcap with HTTP traffic containing a flag in a POST body."""
import os
from scapy.all import Ether, IP, TCP, Raw, wrpcap

FLAG = os.environ.get("FLAG", "CTF{wireshark_http_flag_found}")
OUT  = "/data/capture.pcap"
os.makedirs("/data", exist_ok=True)

CLIENT = "10.0.1.42"
SERVER = "10.0.1.1"
SPORT  = 54321
DPORT  = 80

def tcp(flags, seq, ack, payload=b"", sport=SPORT, dport=DPORT):
    return (Ether() /
            IP(src=CLIENT, dst=SERVER) /
            TCP(sport=sport, dport=dport, flags=flags, seq=seq, ack=ack) /
            (Raw(load=payload) if payload else b""))

def tcp_r(flags, seq, ack, payload=b""):
    return (Ether() /
            IP(src=SERVER, dst=CLIENT) /
            TCP(sport=DPORT, dport=SPORT, flags=flags, seq=seq, ack=ack) /
            (Raw(load=payload) if payload else b""))

# --- decoy GET request (normal traffic) ---
decoy_get = b"GET /index.html HTTP/1.1\r\nHost: intranet.corp\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
decoy_resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 13\r\n\r\n<h1>Hello</h1>"

# --- malicious POST with flag ---
post_body = f"username=admin&password={FLAG}&action=login".encode()
post_req  = (
    b"POST /api/auth HTTP/1.1\r\n"
    b"Host: intranet.corp\r\n"
    b"Content-Type: application/x-www-form-urlencoded\r\n"
    b"User-Agent: python-requests/2.31.0\r\n" +
    f"Content-Length: {len(post_body)}\r\n\r\n".encode() +
    post_body
)
post_resp = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}"

pkts = [
    # Handshake 1
    tcp("S",  seq=1000, ack=0),
    tcp_r("SA", seq=2000, ack=1001),
    tcp("A",  seq=1001, ack=2001),
    # Decoy GET
    tcp("PA", seq=1001, ack=2001, payload=decoy_get),
    tcp_r("A",  seq=2001, ack=1001+len(decoy_get)),
    tcp_r("PA", seq=2001, ack=1001+len(decoy_get), payload=decoy_resp),
    tcp("A",  seq=1001+len(decoy_get), ack=2001+len(decoy_resp)),
    # Teardown
    tcp("FA", seq=1001+len(decoy_get), ack=2001+len(decoy_resp)),
    tcp_r("FA", seq=2001+len(decoy_resp), ack=1001+len(decoy_get)+1),

    # New connection for malicious POST
    tcp("S",  seq=5000, ack=0, sport=54322, dport=80),
    tcp_r("SA", seq=6000, ack=5001),
    tcp("A",  seq=5001, ack=6001, sport=54322),
    tcp("PA", seq=5001, ack=6001, payload=post_req, sport=54322),
    tcp_r("A",  seq=6001, ack=5001+len(post_req)),
    tcp_r("PA", seq=6001, ack=5001+len(post_req), payload=post_resp),
    tcp("A",  seq=5001+len(post_req), ack=6001+len(post_resp), sport=54322),
]

wrpcap(OUT, pkts)
print(f"[+] Generated {len(pkts)} packets → {OUT}")
