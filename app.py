from flask import Flask, request, render_template_string
import sqlite3
import datetime
import os
import requests

app = Flask(__name__)

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
.container { max-width:1000px; margin:auto; }
.card { background:white; padding:20px; border-radius:12px; margin-bottom:20px; }
input, select, textarea, button { width:100%; padding:10px; margin-top:10px; }
button { background:#2563eb; color:white; border:none; }
textarea { height:200px; }
</style>
</head>
<body>
<div class="container">

<h1>🎾 Tennis Partner Finder AI</h1>

<div class="card">
<form method="post">
<input name="nickname" placeholder="Jméno" required>
<select name="city" required>
<option value="">Město</option>
<option>Praha</option>
<option>Brno</option>
</select>
<input name="age" type="number" placeholder="Věk" required>
<select name="level" required>
<option value="">Úroveň</option>
<option>Začátečník</option>
<option>Středně pokročilý</option>
<option>Pokročilý</option>
<option>Profesionál</option>
</select>
<input name="available_time" type="datetime-local" required>
<input name="email" type="email" placeholder="Email" required>
<button>Uložit</button>
</form>
</div>

<div class="card">
<h3>AI odpověď:</h3>
<textarea readonly>{{ match_message }}</textarea>
</div>

<div class="card">
<h3>Hráči:</h3>
{% for p in players %}
<div>{{ p["nickname"] }} - {{ p["city"] }} - {{ p["level"] }}</div>
{% endfor %}
</div>

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

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_players():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM players ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def find_match(player):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM players
        WHERE id != ? AND city = ? AND level = ?
    """, (player["id"], player["city"], player["level"])).fetchall()
    conn.close()

    player_time = datetime.datetime.fromisoformat(player["available_time"])
    best = None
    best_diff = None

    for r in rows:
        t = datetime.datetime.fromisoformat(r["available_time"])
        diff = int(abs((t - player_time).total_seconds()) / 60)

        if diff <= 60:
            if best_diff is None or diff < best_diff:
                best = r
                best_diff = diff

    return best, best_diff

# 🔥 FORMÁLNÍ ODPOVĚĎ
def local_message(match, diff):
    if not match:
        return (
            "V tuto chvíli nebyl nalezen žádný vhodný hráč ke hře.\n"
            "Zkuste upravit termín nebo to opakujte později."
        )

    dt = datetime.datetime.fromisoformat(match["available_time"])
    date_str = dt.strftime("%d.%m.%Y")
    time_str = dt.strftime("%H:%M")

    if diff == 0:
        time_info = "Váš čas se shoduje."
    else:
        time_info = f"Čas se liší o {diff} minut."

    return (
        "Byl nalezen vhodný hráč ke hře.\n\n"
        f"Město: {match['city']}\n"
        f"Úroveň: {match['level']}\n"
        f"Věk: {match['age']} let\n"
        f"Termín: {date_str} v {time_str}\n\n"
        f"{time_info}\n"
        f"Kontaktujte hráče na e-mailu: {match['email']}"
    )

def ai_message(player, match, diff):
    if not OPENAI_API_KEY:
        return local_message(match, diff)

    if not match:
        prompt = (
            "Napiš krátkou formální odpověď v češtině. "
            "Nebyl nalezen žádný hráč ke hře."
        )
    else:
        prompt = (
            f"Byl nalezen hráč: {match['city']}, {match['level']}, {match['age']} let, "
            f"{match['available_time']}, {match['email']}, rozdíl {diff} minut. "
            "Napiš formální odpověď. "
            "Začni: Byl nalezen vhodný hráč ke hře."
        )

    try:
        response = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except:
        return local_message(match, diff)

@app.route("/", methods=["GET", "POST"])
def home():
    match_message = "Po uložení hráče se zobrazí výsledek."

    if request.method == "POST":
        d = request.form

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO players (nickname, city, age, level, available_time, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d["nickname"],
            d["city"],
            int(d["age"]),
            d["level"],
            d["available_time"],
            d["email"]
        ))
        player_id = cur.lastrowid
        conn.commit()

        player = conn.execute("SELECT * FROM players WHERE id=?", (player_id,)).fetchone()
        conn.close()

        match, diff = find_match(player)
        match_message = local_message(match, diff)

    return render_template_string(
        HTML,
        players=fetch_players(),
        match_message=match_message
    )

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
