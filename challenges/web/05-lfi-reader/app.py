from flask import Flask, request, render_template_string
import os
from pathlib import Path

app = Flask(__name__)
APP_DIR = Path("/app")

TMPL = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>DocReader</title>
<style>
body{font-family:monospace;background:#0f172a;color:#cbd5e1;margin:0;padding:20px;}
.top{max-width:800px;margin:0 auto;}
h1{color:#38bdf8;border-bottom:1px solid #1e3a5f;padding-bottom:10px;}
.links{display:flex;gap:12px;margin:16px 0;}
a{color:#38bdf8;text-decoration:none;padding:6px 14px;border:1px solid #1e3a5f;border-radius:6px;font-size:13px;}
a:hover{background:#1e3a5f;}
.viewer{background:#020617;border:1px solid #1e3a5f;border-radius:8px;padding:20px;margin-top:16px;}
.viewer h3{color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.5px;margin:0 0 12px;}
pre{margin:0;white-space:pre-wrap;word-break:break-all;font-size:13px;color:#e2e8f0;}
.err{color:#f87171;margin-top:12px;}
</style></head><body>
<div class="top">
<h1>📄 Documentation System</h1>
<div class="links">
  <a href="/?file=docs/readme.txt">README</a>
  <a href="/?file=docs/config.txt">Config</a>
  <a href="/?file=docs/changelog.txt">Changelog</a>
</div>
{% if content is not none %}
<div class="viewer">
  <h3>Fichier : {{ filename }}</h3>
  <pre>{{ content }}</pre>
</div>
{% elif error %}
<p class="err">{{ error }}</p>
{% else %}
<p style="color:#64748b">Sélectionne un fichier dans la liste ci-dessus.</p>
{% endif %}
</div></body></html>"""

@app.route("/")
def index():
    filename = request.args.get("file", "")
    if not filename:
        return render_template_string(TMPL, content=None, error=None, filename=None)

    # INTENTIONALLY VULNERABLE: no path sanitization
    target = Path("/") / filename
    try:
        content = target.read_text(errors="replace")
        return render_template_string(TMPL, content=content, error=None, filename=filename)
    except PermissionError:
        return render_template_string(TMPL, content=None, error=f"Permission refusée : {filename}", filename=filename)
    except FileNotFoundError:
        return render_template_string(TMPL, content=None, error=f"Fichier introuvable : {filename}", filename=filename)
    except Exception as exc:
        return render_template_string(TMPL, content=None, error=str(exc), filename=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
