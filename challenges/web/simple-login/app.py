#!/usr/bin/env python3
"""
Simple Login Challenge - Player Instance Test
A minimal web login form for CTF practice.
"""

from flask import Flask, render_template_string, request, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ChangeMe-InsecureSecret")

FLAG = os.environ.get("FLAG", "CTF{test_flag_simple_login}")
CHALLENGE_NAME = "Simple Login"
DIFFICULTY = "Easy (Warmup)"

# In-memory user database (for demo)
USERS = {
    "admin": "Ch4ll3ng3Password!",
    "player": "PlayerPass123",
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ challenge_name }} - CTF</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #333;
        }
        .container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            padding: 40px;
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            margin-bottom: 10px;
            color: #667eea;
            font-size: 28px;
        }
        .difficulty {
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-bottom: 30px;
        }
        form {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        label {
            font-weight: bold;
            color: #555;
            font-size: 14px;
        }
        input[type="text"],
        input[type="password"] {
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 5px rgba(102, 126, 234, 0.3);
        }
        button {
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .message {
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 15px;
            font-size: 14px;
            text-align: center;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .flag-box {
            background-color: #f0f0f0;
            border: 2px solid #667eea;
            border-radius: 4px;
            padding: 15px;
            margin-top: 20px;
            word-break: break-all;
            font-weight: bold;
            color: #667eea;
        }
        .hints {
            background: #f9f9f9;
            border-left: 4px solid #ff9800;
            padding: 12px;
            margin-top: 20px;
            font-size: 12px;
            color: #666;
        }
        .logout-link {
            text-align: center;
            margin-top: 15px;
        }
        .logout-link a {
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
        }
        .logout-link a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ challenge_name }}</h1>
        <p class="difficulty">{{ difficulty }}</p>

        {% if message %}
        <div class="message {% if error %}error{% else %}success{% endif %}">
            {{ message }}
        </div>
        {% endif %}

        {% if authenticated %}
        <div class="success">
            Welcome, {{ username }}! 🎉
        </div>
        <div class="flag-box">
            {{ flag }}
        </div>
        <p class="hints">
            <strong>💡 Hints:</strong><br>
            • The flag is shown only after authentication<br>
            • Try logging in with different credentials<br>
            • Look for SQL injection vulnerabilities (for practice)
        </p>
        <div class="logout-link">
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
        {% else %}
        <form method="POST" action="{{ url_for('login') }}">
            <div>
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" placeholder="admin" required>
            </div>
            <div>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" placeholder="••••••" required>
            </div>
            <button type="submit">Login</button>
        </form>
        <p class="hints">
            <strong>💡 Hints for players:</strong><br>
            • Try common credentials: admin / Ch4ll3ng3Password!<br>
            • Test basic SQL injection: admin' --<br>
            • File contains default users
        </p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    authenticated = "user_id" in session
    username = session.get("username", "Guest")
    message = request.args.get("msg", "")
    error = request.args.get("error", "") == "1"

    return render_template_string(
        HTML_TEMPLATE,
        authenticated=authenticated,
        username=username,
        flag=FLAG,
        challenge_name=CHALLENGE_NAME,
        difficulty=DIFFICULTY,
        message=message,
        error=error,
    )

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return redirect(url_for("index", msg="Username and password required", error="1"))

    # Simple auth (no SQL injection protection - for educational purposes)
    if username in USERS and USERS[username] == password:
        session["user_id"] = username
        session["username"] = username
        return redirect(url_for("index", msg=f"Login successful! Welcome, {username}!"))
    else:
        return redirect(url_for("index", msg="Invalid credentials", error="1"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index", msg="Logged out successfully"))

@app.route("/health")
def health():
    return {"status": "ok", "challenge": CHALLENGE_NAME}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
