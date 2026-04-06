from flask import Flask, request, render_template_string
import os
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path("/tmp/auth_sqli_lab.db")
FLAG = os.getenv("FLAG", "CTF{sqli_auth_bypass_master}")

HTML = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Auth SQLi Lab</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 780px; margin: 30px auto; padding: 0 16px; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-top: 16px; }
    input { width: 100%; padding: 10px; margin: 8px 0; }
    button { padding: 10px 14px; }
    .msg { margin-top: 12px; padding: 10px; border-radius: 6px; }
    .ok { background: #e8f7ec; border: 1px solid #9cd9ab; }
    .err { background: #fdeceb; border: 1px solid #f2a9a4; }
    code { background: #f5f5f5; padding: 2px 5px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>Auth SQLi Lab</h1>
  <p>Objective: reach admin session and retrieve the flag.</p>
  <div class=\"card\">
    <form method=\"post\" action=\"/login\">
      <label>Username</label>
      <input name=\"username\" placeholder=\"username\" required>
      <label>Password</label>
      <input name=\"password\" type=\"password\" placeholder=\"password\" required>
      <button type=\"submit\">Login</button>
    </form>
  </div>

  {% if message %}
    <div class=\"msg {{ kind }}\">{{ message }}</div>
  {% endif %}

  <div class=\"card\">
    <h3>Hint</h3>
    <p>The login backend uses an unsafe SQL query built from raw user input.</p>
  </div>
</body>
</html>
"""


def init_db() -> None:
    if DB_PATH.exists():
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "S3curePass2026!"))
    cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("guest", "guest"))
    conn.commit()
    conn.close()


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML, message=None)


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Intentionally vulnerable for educational CTF usage.
    query = f"SELECT username FROM users WHERE username = '{username}' AND password = '{password}'"

    try:
        row = cur.execute(query).fetchone()
    except sqlite3.Error:
        row = None

    conn.close()

    if row and row[0] == "admin":
        return render_template_string(HTML, message=f"Admin access granted. Flag: {FLAG}", kind="ok")

    if row:
        return render_template_string(HTML, message=f"Authenticated as {row[0]}, but admin is required.", kind="err")

    return render_template_string(HTML, message="Invalid credentials.", kind="err")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
