# Stage 1 — compile
FROM gcc:13 AS builder
WORKDIR /src
COPY reverse/03-xor-checker/xor_checker.c .
RUN gcc -O1 -o /xor_checker xor_checker.c && strip /xor_checker

# Stage 2 — serve
FROM python:3.11-slim
RUN pip install --no-cache-dir flask
RUN mkdir -p /data
COPY --from=builder /xor_checker /data/xor_checker
COPY forensics/serve.py /app/serve.py
ENV CHALLENGE_FILE=xor_checker
ENV CHALLENGE_TITLE="XOR Checker (Linux x86-64)"
ENV CHALLENGE_DESC="Un binaire Linux valide une clé via XOR à masque répété. Reverse le XOR pour trouver la bonne clé."
ENV CHALLENGE_CATEGORY="Reverse Engineering"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
