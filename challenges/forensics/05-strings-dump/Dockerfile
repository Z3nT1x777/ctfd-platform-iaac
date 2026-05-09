FROM python:3.11-slim
RUN pip install --no-cache-dir flask
WORKDIR /app
COPY generate.py /generate.py
ARG FLAG=CTF{strings_memdump_analysis}
ENV FLAG=${FLAG}
RUN python /generate.py
COPY ../serve.py /app/serve.py
ENV CHALLENGE_FILE=memdump.strings
ENV CHALLENGE_TITLE="Memory Dump — Strings"
ENV CHALLENGE_DESC="Extraction des chaînes d'un processus suspect. 3600 lignes. Une seule contient le flag."
ENV CHALLENGE_CATEGORY="Forensics"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
