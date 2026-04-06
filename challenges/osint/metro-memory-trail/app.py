from flask import Flask, send_from_directory
from pathlib import Path

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
ASSETS = SITE / "assets"


@app.route("/")
def index():
    return send_from_directory(SITE, "index.html")


@app.route("/assets/<path:filename>")
def asset(filename: str):
    return send_from_directory(ASSETS, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
