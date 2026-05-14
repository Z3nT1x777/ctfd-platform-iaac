from flask import Flask, request, render_template_string
import os, sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path("/tmp/sqli.db")
FLAG = os.environ.get("FLAG", "CTF{sqli_auth_bypass_union_select}")

HTML = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Corporate Portal</title>
<style>
body{font-family:Arial,sans-serif;background:#0a0e1a;color:#cdd;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
.card{background:#111827;border:1px solid #1f2d40;border-radius:12px;padding:40px;width:380px;}
h2{color:#38bdf8;text-align:center;margin-bottom:6px;font-size:1.3rem;}
p.sub{text-align:center;color:#6b7280;font-size:12px;margin-bottom:24px;}
label{display:block;font-size:12px;color:#9ca3af;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px;}
input{width:100%;padding:10px;margin-bottom:16px;background:#1f2937;border:1px solid #374151;border-radius:6px;color:#f9fafb;box-sizing:border-box;}
button{width:100%;padding:12px;background:#0284c7;border:none;border-radius:6px;color:#fff;font-weight:bold;cursor:pointer;}
.msg{padding:10px 14px;border-radius:6px;margin-bottom:16px;font-size:13px;}
.ok{background:#064e3b;border:1px solid #059669;color:#6ee7b7;}
.err{background:#450a0a;border:1px solid #dc2626;color:#fca5a5;}
code{background:#0f172a;padding:2px 6px;border-radius:4px;font-size:12px;}
</style></head><body>
<div class="card">
  <h2>🏢 Corporate Portal</h2>
  <p class="sub">Accès restreint aux employés autorisés</p>
  {% if message %}<div class="msg {{ kind }}">{{ message }}</div>{% endif %}
  <form method="POST" action="/login">
    <label>Username</label><input name="username" placeholder="john.doe">
    <label>Password</label><input name="password" type="password" placeholder="••••••••">
    <button>Se connecter</button>
  </form>
</div></body></html>"""

def init_db():
    if DB.exists(): return
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    conn.execute("INSERT INTO users VALUES(1,'admin','Sup3rS3cr3tP@ss!','admin')")
    conn.execute("INSERT INTO users VALUES(2,'alice','alice2024','user')")
    conn.execute("INSERT INTO users VALUES(3,'bob','bob2024','user')")
    conn.commit(); conn.close()

@app.route("/")
def index():
    return render_template_string(HTML, message=None, kind="ok")

@app.route("/login", methods=["POST"])
def login():
    u = request.form.get("username",""); p = request.form.get("password","")
    conn = sqlite3.connect(DB); cur = conn.cursor()
    # INTENTIONALLY VULNERABLE
    q = f"SELECT username, role FROM users WHERE username='{u}' AND password='{p}'"
    try: row = cur.execute(q).fetchone()
    except sqlite3.Error: row = None
    conn.close()
    if row and row[1] == "admin":
        return render_template_string(HTML, message=f"✅ Bienvenue {row[0]} ! Flag : {FLAG}", kind="ok")
    if row:
        return render_template_string(HTML, message=f"Connecté en tant que {row[0]}, mais accès admin requis.", kind="err")
    return render_template_string(HTML, message="Identifiants invalides.", kind="err")

if __name__ == "__main__":
    init_db(); app.run(host="0.0.0.0", port=5000)
