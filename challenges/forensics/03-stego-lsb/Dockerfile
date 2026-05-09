FROM python:3.11-slim
RUN pip install --no-cache-dir flask pillow
WORKDIR /app
COPY 03-stego-lsb/generate.py /generate.py
ARG FLAG=CTF{lsb_pixels_dont_lie}
ENV FLAG=${FLAG}
RUN python /generate.py
COPY serve.py /app/serve.py
ENV CHALLENGE_FILE=landscape.png
ENV CHALLENGE_TITLE="Stéganographie LSB"
ENV CHALLENGE_DESC="Un message secret a été dissimulé dans cette photo de paysage. Analyse les pixels pour retrouver le flag caché."
ENV CHALLENGE_CATEGORY="Forensics"
EXPOSE 5000
CMD ["python", "/app/serve.py"]
