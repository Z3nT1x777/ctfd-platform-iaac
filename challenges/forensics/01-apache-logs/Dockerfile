FROM python:3.11-slim
RUN pip install --no-cache-dir flask
WORKDIR /app
COPY generate.py /generate.py
ARG FLAG=CTF{apache_log_never_lies}
ENV FLAG=${FLAG}
RUN python /generate.py
COPY ../serve.py /app/serve.py
ENV CHALLENGE_FILE=access.log
ENV CHALLENGE_TITLE="Apache Log Analysis"
ENV CHALLENGE_DESC="Un serveur interne a été compromis. Analyse les logs Apache et retrouve la donnée exfiltrée."
ENV CHALLENGE_CATEGORY="Forensics"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
