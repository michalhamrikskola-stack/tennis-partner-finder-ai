from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import datetime
import requests

app = Flask(__name__)

DB_PATH = "/tmp/players.db"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gemma3:27b")

HTML = """
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tennis Partner Finder AI</title>

<style>
body { margin:0; font-family:Arial; background:#f4f7fb; }

.container { max-width:1100px; margin:auto; padding:20px; }

.hero {
    background:linear-gradient(135deg,#0f172a,#1e3a8a);
    color:white;
    border-radius:20px;
    padding:25px;
    margin-bottom:20px;
}

.hero h1 { margin:0; font-size:32px; }

.grid {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:20px;
}

.card {
    background:white;
    border-radius:18px;
    padding:20px;
    box-shadow:0 10px 25px rgba(0,0,0,0.08);
}

label { font-weight:bold; margin-top:10px; display:block; }

input, select, textarea {
    width:100%;
    padding:12px;
    margin-top:5px;
    border-radius:10px;
    border:1px solid #ccc;
}

button {
    margin-top:15px;
    width:100%;
    padding:12px;
    border:none;
    border-radius:10px;
    background:#2563eb;
    color:white;
    font-weight:bold;
    cursor:pointer;
}

textarea { height:260px; background:#f8fbff; }

.success {
    background:#e8f7ee;
    color:#196c3b;
    padding:10px;
    border-radius:10px;
    margin-bottom:10px;
}

@media(max-width:900px){
    .grid{grid-template-columns:1fr;}
}
</style>
</head>

<body>
<div class="container">

<div class="hero">
<h1>🎾 Tennis Partner Finder AI</h1>
<p>Najdi spoluhráče podle města, úrovně a času.</p>
</div>

<div class="grid">

<div class="card">
<h2>Nový hráč</h2>

{% if message %}
<div class="success">{{ message }}</div>
{% endif %}

<form method="post">

<label>Jméno</label>
<input name="nickname" required>

<label>Město</label>
<select name="city" required>
<option value="">Vyber město</option>
<option>Praha</option>
<option>Brno</option>
</select>

<label>Věk</label>
<input name="age" type="number" required>

<label>Úroveň</label>
<select name="level" required>
<option value="">Vyber úroveň</option>
<option>Začátečník</option>
<option>Středně pokročilý</option>
<option>Pokročilý</option>
<option>Profesionál</option>
</select>

<label>Kdy může hrát</label>
<input name="available_time" type="datetime-local" required>

<label>Email</label>
<input name="email" type="email" required>

<button>Uložit hráče</button>

</form>
</div>

<div class="card">
<h2>AI odpověď</h2>
<textarea readonly>{{ match_message }}</textarea>
</div>

</div>

<div class="card">
<h2>Hráči</h2>
{% for p in players %}
<div>{{ p["nickname"] }} – {{ p["city"] }} – {{ p["level"] }}</div>
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

    for r in rows:
        t = datetime.datetime.fromisoformat(r["available_time"])
        diff = int(abs((t - player_time).total_seconds()) / 60)

        if diff <= 60:
            return r, diff

    return None, None

# 🔥 TADY JE OPRAVENÁ ODPOVĚĎ
def ai_match_message(player, match, diff):
    if not match:
        return (
            "V tuto chvíli nebyl nalezen žádný vhodný hráč ke hře.\n"
            "Zkuste upravit termín nebo to opakujte později."
        )

    dt = datetime.datetime.fromisoformat(match["available_time"])
    date_str = dt.strftime("%d.%m.%Y")
    time_str = dt.strftime("%H:%M")

    if diff == 0:
        time_text = "Váš čas se plně shoduje."
    else:
        time_text = f"Čas se liší o {diff} minut."

    return (
        "Byl nalezen vhodný hráč ke hře.\n\n"
        f"Město: {match['city']}\n"
        f"Úroveň: {match['level']}\n"
        f"Věk: {match['age']} let\n"
        f"Datum: {date_str}\n"
        f"Hodina: {time_str}\n\n"
        f"{time_text}\n"
        f"Kontaktujte hráče: {match['email']}"
    )

@app.route("/", methods=["GET","POST"])
def home():
    match_message = "Po uložení hráče se zobrazí výsledek."
    message = None

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
        match_message = ai_match_message(player, match, diff)
        message = "Hráč byl uložen."

    return render_template_string(
        HTML,
        players=fetch_players(),
        match_message=match_message,
        message=message
    )

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
