FROM python:3.11-slim
RUN pip install --no-cache-dir flask scapy
WORKDIR /app
COPY 04-pcap-dns/generate.py /generate.py
ARG FLAG=CTF{dns_tunnel_data_exfil}
ENV FLAG=${FLAG}
RUN python /generate.py
COPY serve.py /app/serve.py
ENV CHALLENGE_FILE=dns_traffic.pcap
ENV CHALLENGE_TITLE="DNS Exfiltration"
ENV CHALLENGE_DESC="Un malware a exfiltré des données via DNS. Analyse la capture et reconstitue le message caché dans les requêtes."
ENV CHALLENGE_CATEGORY="Forensics"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
