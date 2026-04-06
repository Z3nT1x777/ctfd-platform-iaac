FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY flag.txt /flag.txt

ENV FLAG=CTF{sqli_auth_bypass_master}
EXPOSE 5000

CMD ["python", "app.py"]