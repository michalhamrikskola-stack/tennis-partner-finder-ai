from flask import Flask, request, render_template_string
import sqlite3
import datetime

app = Flask(__name__)

DB_PATH = "/data/players.db"

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
}

textarea { height:250px; }

.player {
    padding:10px;
    border-bottom:1px solid #eee;
}
</style>
</head>

<body>
<div class="container">

<div class="hero">
<h1>🎾 Tennis Partner Finder AI</h1>
<p>Najdi spoluhráče podle města, úrovně a času</p>
</div>

<div class="grid">

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
<input name="email" placeholder="Email" required>

<button>Uložit</button>
</form>
</div>

<div class="card">
<textarea readonly>{{ match_message }}</textarea>
</div>

</div>

<div class="card">
<h2>Hráči</h2>
{% for p in players %}
<div class="player">
<b>{{ p["nickname"] }}</b> – {{ p["city"] }} – {{ p["level"] }}<br>
🕒 {{ p["available_time"].replace("T"," ") }}
</div>
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
    SELECT * FROM players WHERE id != ? AND city = ? AND level = ?
    """, (player["id"], player["city"], player["level"])).fetchall()
    conn.close()

    player_time = datetime.datetime.fromisoformat(player["available_time"])

    for r in rows:
        t = datetime.datetime.fromisoformat(r["available_time"])
        diff = int(abs((t - player_time).total_seconds()) / 60)

        if diff <= 60:
            return r, diff

    return None, None

def ai_match_message(player, match, diff):
    if not match:
        return "Nebyl nalezen žádný hráč."

    dt = datetime.datetime.fromisoformat(match["available_time"])

    return f"""Byl nalezen hráč:

Město: {match['city']}
Úroveň: {match['level']}
Čas: {dt.strftime('%H:%M')}

Kontakt: {match['email']}
"""

@app.route("/", methods=["GET","POST"])
def home():
    match_message = "Výsledek se zobrazí zde"

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

        pid = cur.lastrowid
        conn.commit()

        player = conn.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
        conn.close()

        match, diff = find_match(player)
        match_message = ai_match_message(player, match, diff)

    return render_template_string(
        HTML,
        players=fetch_players(),
        match_message=match_message
    )

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
