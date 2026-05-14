# Soluce — 02-pcap-http

## Contexte

Un fichier `.pcap` contient du trafic réseau. Une requête HTTP POST transmet des credentials dont le flag dans le champ `password`.

## Étapes de résolution

### Méthode 1 — Wireshark (GUI)

1. Ouvrir le fichier avec Wireshark
2. Filtre d'affichage : `http.request.method == "POST"`
3. Sélectionner le paquet POST
4. Dérouler la section **Hypertext Transfer Protocol** puis **HTML Form URL Encoded**
5. Le champ `password` contient le flag

### Méthode 2 — strings

```bash
# Chercher directement le flag dans les bytes bruts
strings capture.pcap | grep "CTF{"

# Ou chercher le champ password
strings capture.pcap | grep "password="
```

### Méthode 3 — tshark (ligne de commande)

```bash
# Extraire les données des requêtes HTTP POST
tshark -r capture.pcap -Y "http.request.method==POST" -T fields -e http.file_data

# Ou suivre le flux TCP et décoder
tshark -r capture.pcap -z follow,tcp,ascii,0
```

### Méthode Python (scapy)

```python
from scapy.all import rdpcap, Raw

pkts = rdpcap("capture.pcap")
for pkt in pkts:
    if pkt.haslayer(Raw):
        payload = pkt[Raw].load.decode(errors='ignore')
        if "password=" in payload:
            print(payload)
```

## Correction

La requête POST vers `/login` contient :

```
POST /login HTTP/1.1
Content-Type: application/x-www-form-urlencoded

username=admin&password=CTF{wireshark_http_flag_found}
```

**Flag : `CTF{wireshark_http_flag_found}`**
