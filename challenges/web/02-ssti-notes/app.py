from flask import Flask, request, render_template_string
import os

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "CTF{jinja2_ssti_oops}")

BASE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>MyNotes</title>
<style>
body{font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px;}
.container{max-width:680px;margin:40px auto;background:#fff;border-radius:12px;padding:30px;box-shadow:0 2px 12px rgba(0,0,0,.08);}
h1{color:#333;margin-bottom:4px;}p.sub{color:#888;font-size:13px;margin-bottom:20px;}
textarea{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:14px;resize:vertical;min-height:100px;box-sizing:border-box;}
button{padding:10px 20px;background:#4f46e5;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:14px;margin-top:10px;}
.note-box{background:#f9f9f9;border:1px solid #eee;border-radius:8px;padding:16px;margin-top:20px;}
.note-box h3{margin:0 0 10px;font-size:14px;color:#555;text-transform:uppercase;letter-spacing:.5px;}
</style></head><body>
<div class="container">
  <h1>📝 MyNotes</h1>
  <p class="sub">Prends des notes rapidement</p>
  <form method="POST">
    <textarea name="note" placeholder="Écris ta note ici...">{{ raw_note }}</textarea><br>
    <button type="submit">Enregistrer</button>
  </form>
  {% if rendered_note is not none %}
  <div class="note-box">
    <h3>Ta note</h3>
    <div>""" + "{{ rendered_note }}" + """</div>
  </div>
  {% endif %}
</div></body></html>"""

@app.route("/", methods=["GET", "POST"])
def index():
    raw_note = ""
    rendered_note = None
    if request.method == "POST":
        raw_note = request.form.get("note", "")
        # INTENTIONALLY VULNERABLE: renders user input as Jinja2 template
        try:
            rendered_note = render_template_string(raw_note)
        except Exception as e:
            rendered_note = f"[Erreur de template: {e}]"
    return render_template_string(BASE, raw_note=raw_note, rendered_note=rendered_note)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
