# Stage 1 — compile
FROM gcc:13 AS builder
WORKDIR /src
COPY checker.c .
RUN gcc -O1 -o /crackme checker.c && strip /crackme

# Stage 2 — serve
FROM python:3.11-slim
RUN pip install --no-cache-dir flask
RUN mkdir -p /data
COPY --from=builder /crackme /data/crackme
COPY ../../forensics/serve.py /app/serve.py
ENV CHALLENGE_FILE=crackme
ENV CHALLENGE_TITLE="License Checker (Linux x86-64)"
ENV CHALLENGE_DESC="Un binaire Linux vérifie une clé de licence. Télécharge-le et reverse-le pour trouver la bonne clé."
ENV CHALLENGE_CATEGORY="Reverse Engineering"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
