FROM python:3.11-slim
RUN pip install --no-cache-dir flask
WORKDIR /app
COPY 06-zip-hidden/generate.py /generate.py
ARG FLAG=CTF{zip_comment_forensics}
ENV FLAG=${FLAG}
RUN python /generate.py
COPY serve.py /app/serve.py
ENV CHALLENGE_FILE=evidence.zip
ENV CHALLENGE_TITLE="ZIP Hidden Data"
ENV CHALLENGE_DESC="Un fichier ZIP suspect. Les fichiers semblent normaux... mais le format ZIP cache bien des secrets."
ENV CHALLENGE_CATEGORY="Forensics"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
