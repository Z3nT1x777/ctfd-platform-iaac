from flask import Flask, request, render_template_string, session, redirect
import os, random

app = Flask(__name__)
app.secret_key = "ctf-idor-secret"
FLAG = os.environ.get("FLAG", "CTF{idor_user_enumeration_owned}")

PROFILES = {
    1: {"name": "Administrator", "bio": "Compte admin du système.", "flag": FLAG},
    2: {"name": "CTF Bot", "bio": "Compte de test automatisé.", "flag": None},
}

TMPL = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>SocialCTF</title>
<style>
body{font-family:Arial,sans-serif;background:#18181b;color:#f4f4f5;margin:0;}
nav{background:#09090b;padding:14px 24px;display:flex;align-items:center;gap:16px;border-bottom:1px solid #27272a;}
nav a{color:#a1a1aa;text-decoration:none;font-size:14px;}nav a:hover{color:#fff;}
nav strong{color:#fff;font-size:16px;flex:1;}
.container{max-width:600px;margin:40px auto;padding:0 20px;}
.profile-card{background:#27272a;border:1px solid #3f3f46;border-radius:12px;padding:28px;}
.avatar{width:72px;height:72px;background:#6d28d9;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;margin-bottom:16px;}
h2{margin:0 0 4px;font-size:1.3rem;}
p.bio{color:#a1a1aa;font-size:14px;margin:8px 0 16px;}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;}
.badge-admin{background:#5b21b6;color:#ddd6fe;}
.badge-user{background:#1e3a5f;color:#93c5fd;}
.flag{background:#14532d;border:1px solid #16a34a;border-radius:8px;padding:14px;margin-top:16px;font-family:monospace;font-size:13px;color:#86efac;word-break:break-all;}
a.btn{display:inline-block;padding:8px 16px;background:#6d28d9;color:#fff;border-radius:8px;text-decoration:none;font-size:13px;margin-top:12px;}
.err{background:#450a0a;border:1px solid #dc2626;color:#fca5a5;border-radius:8px;padding:14px;}
</style></head><body>
<nav>
  <strong>🌐 SocialCTF</strong>
  <a href="/profile?user_id={{ my_id }}">Mon profil (ID: {{ my_id }})</a>
</nav>
<div class="container">
  {% if profile %}
  <div class="profile-card">
    <div class="avatar">{{ profile.name[0] }}</div>
    <h2>{{ profile.name }}</h2>
    <span class="badge {% if uid == 1 %}badge-admin{% else %}badge-user{% endif %}">
      {% if uid == 1 %}admin{% else %}user{% endif %}
    </span>
    <p class="bio">{{ profile.bio }}</p>
    <small style="color:#71717a">Profil #{{ uid }}</small>
    {% if profile.flag %}
    <div class="flag">🎉 {{ profile.flag }}</div>
    {% endif %}
  </div>
  {% else %}
  <div class="err">Utilisateur #{{ uid }} introuvable.</div>
  {% endif %}
</div></body></html>"""

@app.route("/")
def index():
    if "uid" not in session:
        session["uid"] = random.randint(50, 999)
    return redirect(f"/profile?user_id={session['uid']}")

@app.route("/profile")
def profile():
    if "uid" not in session:
        session["uid"] = random.randint(50, 999)
    my_id = session["uid"]
    try:
        uid = int(request.args.get("user_id", my_id))
    except ValueError:
        uid = my_id
    # INTENTIONALLY VULNERABLE: no ownership check
    profile = PROFILES.get(uid)
    return render_template_string(TMPL, profile=profile, uid=uid, my_id=my_id)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
