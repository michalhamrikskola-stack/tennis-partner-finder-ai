from flask import Flask, request, render_template_string
import sqlite3
import datetime
import os

app = Flask(__name__)

DB_PATH = "/data/players.db"

HTML = """... (TVŮJ HTML NECHÁVÁM STEJNÝ, nemusíš řešit) ...
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

# 🔥 TADY JE TA DATABÁZE (NOVĚ)
@app.route("/db")
def show_db():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT * FROM players").fetchall()
    conn.close()

    output = ""
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
