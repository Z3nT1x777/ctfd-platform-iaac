from flask import Flask, request, render_template_string, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = "ctf-static-secret"
FLAG = os.environ.get("FLAG", "CTF{default_creds_are_dangerous}")

USERS = {"admin": "admin123", "guest": "guest"}

TMPL = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Admin Panel</title>
<style>
body{font-family:Arial,sans-serif;background:#1a1a2e;color:#eee;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
.card{background:#16213e;border:1px solid #0f3460;border-radius:12px;padding:40px;width:340px;}
h2{text-align:center;color:#e94560;margin-bottom:24px;}
input{width:100%;padding:10px;margin:8px 0 16px;background:#0f3460;border:1px solid #e94560;border-radius:6px;color:#eee;box-sizing:border-box;}
button{width:100%;padding:12px;background:#e94560;border:none;border-radius:6px;color:#fff;font-weight:bold;cursor:pointer;font-size:15px;}
.msg{padding:10px;border-radius:6px;margin-bottom:16px;text-align:center;}
.ok{background:#1a4731;border:1px solid #34d399;color:#34d399;}
.err{background:#4b1b1b;border:1px solid #f87171;color:#f87171;}
.flag{background:#0f3460;border:1px solid #e94560;border-radius:8px;padding:16px;margin-top:16px;word-break:break-all;font-family:monospace;color:#e94560;font-size:13px;}
a{color:#e94560;text-decoration:none;display:block;text-align:center;margin-top:12px;}
</style></head><body>
<div class="card">
  <h2>🔐 Admin Panel</h2>
  {% if msg %}<div class="msg {{ kind }}">{{ msg }}</div>{% endif %}
  {% if flag %}
    <div class="msg ok">Authentifié en tant que {{ user }} !</div>
    <div class="flag">{{ flag }}</div>
    <a href="/logout">Se déconnecter</a>
  {% else %}
    <form method="POST">
      <input name="username" placeholder="Username" required>
      <input name="password" type="password" placeholder="Password" required>
      <button type="submit">Connexion</button>
    </form>
  {% endif %}
</div></body></html>"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u in USERS and USERS[u] == p:
            session["user"] = u
            return redirect("/")
        return render_template_string(TMPL, msg="Identifiants incorrects", kind="err", flag=None, user=None)
    user = session.get("user")
    flag = FLAG if user == "admin" else None
    msg = "Connecté — mais vous n'êtes pas admin." if user and user != "admin" else None
    return render_template_string(TMPL, flag=flag, user=user, msg=msg, kind="err")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
