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
    box-sizing:border-box;
}

button {
    margin-top:15px;
    width:100%;
    padding:12px;
    border:none;
    border-radius:10px;
    background:#2563eb;
    color:white;
    cursor:pointer;
    font-weight:bold;
}

textarea { height:250px; }

.player {
    padding:10px;
    border-bottom:1px solid #eee;
}

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
<p>Najdi spoluhráče podle města, úrovně a času</p>
</div>

<div class="grid">

<div class="card">
{% if message %}
<div class="success">{{ message }}</div>
{% endif %}

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
<h2>AI odpověď</h2>
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

@app.route("/", methods=["GET", "POST"])
def home():
    match_message = "Výsledek se zobrazí zde"
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

        pid = cur.lastrowid
        conn.commit()

        player = conn.execute("SELECT * FROM players WHERE id = ?", (pid,)).fetchone()
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

@app.route("/ping")
def ping():
    return "pong"

@app.route("/db")
def show_db():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM players").fetchall()
    conn.close()

    output = "<h1>Databáze hráčů</h1>"
    for r in rows:
        output += f"""
        <p>
        ID: {r[0]}<br>
        Jméno: {r[1]}<br>
        Město: {r[2]}<br>
        Věk: {r[3]}<br>
        Úroveň: {r[4]}<br>
        Čas: {r[5]}<br>
        Email: {r[6]}
        </p>
        <hr>
        """
    return output

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
