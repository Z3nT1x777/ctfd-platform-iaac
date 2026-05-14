from flask import Flask, request, render_template_string, jsonify
import os, jwt as pyjwt

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "CTF{jwt_weak_secret_cracked}")
JWT_SECRET = "secret123"  # INTENTIONALLY WEAK

TMPL = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>JWT API Lab</title>
<style>
body{font-family:Arial,sans-serif;background:#0a0e1a;color:#e2e8f0;margin:0;padding:24px;}
.container{max-width:700px;margin:0 auto;}
h1{color:#f59e0b;border-bottom:1px solid #1e3a5f;padding-bottom:10px;}
.card{background:#111827;border:1px solid #1f2d40;border-radius:10px;padding:20px;margin:16px 0;}
.card h3{color:#f59e0b;margin:0 0 10px;font-size:1rem;}
input,textarea{width:100%;padding:10px;background:#1f2937;border:1px solid #374151;border-radius:6px;color:#f9fafb;box-sizing:border-box;font-family:monospace;font-size:13px;}
textarea{height:80px;resize:vertical;}
button{padding:10px 20px;background:#d97706;border:none;border-radius:6px;color:#fff;font-weight:bold;cursor:pointer;margin-top:10px;}
pre{background:#020617;border:1px solid #1e3a5f;border-radius:6px;padding:12px;font-size:12px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;}
.ok{border-color:#059669!important;color:#6ee7b7;}
.err{border-color:#dc2626!important;color:#fca5a5;}
label{display:block;font-size:12px;color:#9ca3af;margin-bottom:4px;margin-top:12px;}
</style></head><body>
<div class="container">
<h1>🔑 JWT API Lab</h1>
<div class="card">
  <h3>1. Obtenir un token (guest)</h3>
  <p style="color:#9ca3af;font-size:13px;margin-bottom:12px">Login avec les credentials guest / guest pour recevoir un JWT.</p>
  <form id="loginForm">
    <label>Username</label><input id="uname" value="guest">
    <label>Password</label><input id="pass" value="guest" type="password">
    <button type="button" onclick="doLogin()">Se connecter</button>
  </form>
  <pre id="tokenOut" style="margin-top:12px;display:none"></pre>
</div>
<div class="card">
  <h3>2. Accéder au flag (rôle admin requis)</h3>
  <p style="color:#9ca3af;font-size:13px;margin-bottom:12px">Envoie ton JWT dans le header <code>Authorization: Bearer &lt;token&gt;</code>.</p>
  <label>Token JWT</label><textarea id="tokenInput" placeholder="eyJ..."></textarea>
  <button type="button" onclick="tryFlag()">Tenter l'accès</button>
  <pre id="flagOut" style="margin-top:12px;display:none"></pre>
</div>
</div>
<script>
async function doLogin() {
  const r = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({username: document.getElementById('uname').value, password: document.getElementById('pass').value})});
  const d = await r.json();
  const el = document.getElementById('tokenOut');
  el.style.display='block';
  el.className = d.token ? 'ok' : 'err';
  el.textContent = JSON.stringify(d, null, 2);
  if (d.token) document.getElementById('tokenInput').value = d.token;
}
async function tryFlag() {
  const tok = document.getElementById('tokenInput').value.trim();
  const r = await fetch('/api/flag', {headers: {'Authorization': 'Bearer ' + tok}});
  const d = await r.json();
  const el = document.getElementById('flagOut');
  el.style.display='block';
  el.className = d.flag ? 'ok' : 'err';
  el.textContent = JSON.stringify(d, null, 2);
}
</script>
</body></html>"""

@app.route("/")
def index():
    return render_template_string(TMPL)

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    u, p = data.get("username",""), data.get("password","")
    if u == "guest" and p == "guest":
        token = pyjwt.encode({"user": "guest", "role": "guest"}, JWT_SECRET, algorithm="HS256")
        return jsonify({"token": token, "role": "guest"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/flag")
def flag():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing token"}), 401
    token = auth.split(" ", 1)[1]
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid token: {e}"}), 401
    if payload.get("role") != "admin":
        return jsonify({"error": "Forbidden — admin role required", "your_role": payload.get("role")}), 403
    return jsonify({"flag": FLAG, "user": payload.get("user")})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
