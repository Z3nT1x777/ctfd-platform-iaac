FROM python:3.11-slim
RUN pip install --no-cache-dir flask scapy
WORKDIR /app
COPY generate.py /generate.py
ARG FLAG=CTF{wireshark_http_flag_found}
ENV FLAG=${FLAG}
RUN python /generate.py
COPY ../serve.py /app/serve.py
ENV CHALLENGE_FILE=capture.pcap
ENV CHALLENGE_TITLE="Network Capture — HTTP"
ENV CHALLENGE_DESC="Une capture réseau a été effectuée sur un poste compromis. Analyse le trafic et retrouve les credentials exfiltrés."
ENV CHALLENGE_CATEGORY="Forensics"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
