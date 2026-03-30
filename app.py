from flask import Flask, request, render_template_string
import sqlite3
import datetime
import os
import requests

app = Flask(__name__)

# 🔥 FUNKČNÍ DB PRO KURIM
DB_PATH = "/tmp/players.db"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gemma3:27b")

HTML = """
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<title>Tennis Partner Finder AI</title>
<style>
body { font-family: Arial; background:#f4f7fb; padding:20px; }
.card { background:white; padding:20px; border-radius:10px; margin-bottom:20px; }
button { padding:10px; background:#2563eb; color:white; border:none; }
</style>
</head>
<body>

<h1>🎾 Tennis Partner Finder AI</h1>

<div class="card">
<form method="post">
<input name="nickname" placeholder="Jméno" required><br><br>
<input name="city" placeholder="Praha / Brno" required><br><br>
<input name="age" type="number" placeholder="Věk" required><br><br>
<input name="level" placeholder="Úroveň" required><br><br>
<input name="available_time" type="datetime-local" required><br><br>
<input name="email" placeholder="Email" required><br><br>
<button>Uložit</button>
</form>
</div>

<div class="card">
<h2>AI odpověď:</h2>
<pre>{{ match_message }}</pre>
</div>

<div class="card">
<h2>Hráči:</h2>
<ul>
{% for p in players %}
<li>{{ p[1] }} - {{ p[2] }} - {{ p[4] }}</li>
{% endfor %}
</ul>
</div>

</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT,
        city TEXT,
        age INTEGER,
        level TEXT,
        available_time TEXT,
        email TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_players():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM players").fetchall()
    conn.close()
    return rows

def find_match(player):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM players WHERE id != ?", (player[0],)).fetchall()
    conn.close()

    player_time = datetime.datetime.fromisoformat(player[5])

    for r in rows:
        candidate_time = datetime.datetime.fromisoformat(r[5])
        diff = abs((candidate_time - player_time).total_seconds()) / 60

        if r[2] == player[2] and r[4] == player[4] and diff <= 60:
            return r, int(diff)

    return None, None

def ai_message(player, match, diff):
    if not OPENAI_API_KEY:
        return "AI není aktivní (chybí API key)."

    if not match:
        prompt = "Nikdo se neshoduje ve stejný čas. Napiš krátkou odpověď."
    else:
        prompt = f"""
Našel se spoluhráč:
{match[1]}, {match[2]}, {match[4]}, email: {match[6]}
rozdíl času: {diff} minut
"""

    try:
        r = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=20
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "AI selhalo, ale match funguje 👍"

@app.route("/", methods=["GET", "POST"])
def home():
    match_message = ""

    if request.method == "POST":
        data = request.form

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO players (nickname, city, age, level, available_time, email)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["nickname"],
            data["city"],
            int(data["age"]),
            data["level"],
            data["available_time"],
            data["email"]
        ))

        pid = cursor.lastrowid
        conn.commit()

        player = conn.execute("SELECT * FROM players WHERE id = ?", (pid,)).fetchone()
        conn.close()

        match, diff = find_match(player)
        match_message = ai_message(player, match, diff)

    return render_template_string(
        HTML,
        players=get_players(),
        match_message=match_message
    )

@app.route("/ping")
def ping():
    return "pong"

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
