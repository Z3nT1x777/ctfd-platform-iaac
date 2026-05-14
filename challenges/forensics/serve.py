"""Common file-download server for forensics/reverse challenges."""
from flask import Flask, send_file, render_template_string
import os

app = Flask(__name__)
FILE      = os.environ.get("CHALLENGE_FILE", "challenge.bin")
TITLE     = os.environ.get("CHALLENGE_TITLE", "Challenge")
DESC      = os.environ.get("CHALLENGE_DESC", "Download and analyse the file.")
CATEGORY  = os.environ.get("CHALLENGE_CATEGORY", "forensics")

TMPL = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{{ title }}</title>
<style>
:root{--bg:#070d16;--card:#101a2a;--fg:#e6edf7;--muted:#8b949e;--line:#2a3548;--blue:#2563eb;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--fg);font-family:"Segoe UI",Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:36px;max-width:560px;width:100%;}
h1{font-size:1.3rem;margin-bottom:6px;}
.cat{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:20px;}
p{color:var(--muted);font-size:14px;line-height:1.6;margin-bottom:24px;}
.dl-btn{display:flex;align-items:center;gap:10px;background:var(--blue);color:#fff;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:600;font-size:14px;width:fit-content;}
.dl-btn:hover{opacity:.85;}
.fname{margin-top:16px;font-family:monospace;font-size:12px;color:var(--muted);}
</style></head><body>
<div class="card">
  <h1>{{ title }}</h1>
  <p class="cat">{{ category }}</p>
  <p>{{ desc }}</p>
  <a class="dl-btn" href="/download">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
      <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
      <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
    </svg>
    Télécharger le fichier
  </a>
  <p class="fname">{{ filename }}</p>
</div></body></html>"""

@app.route("/")
def index():
    return render_template_string(TMPL, title=TITLE, desc=DESC,
                                  category=CATEGORY, filename=FILE)

@app.route("/download")
def download():
    return send_file(f"/data/{FILE}", as_attachment=True,
                     download_name=FILE)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
