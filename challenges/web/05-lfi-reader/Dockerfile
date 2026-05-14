FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY flag.txt /flag.txt
RUN mkdir -p /app/docs && \
    echo "# Documentation\nThis is the main README file.\nVersion: 1.0.0" > /app/docs/readme.txt && \
    echo "[database]\nhost = db.internal\nport = 5432\nname = appdb" > /app/docs/config.txt && \
    echo "v1.0.0 - Initial release\nv1.1.0 - Added file reader" > /app/docs/changelog.txt
EXPOSE 5000
CMD ["python", "app.py"]
