from flask import Flask, request, render_template_string
import sqlite3
import os
import datetime

app = Flask(__name__)

# 🔥 FUNKČNÍ DB
DB_PATH = "/tmp/players.db"

HTML = """
<h1>Tennis Partner Finder AI</h1>

<form method="post">
<input name="nickname" placeholder="Jméno" required><br>
<input name="city" placeholder="Praha / Brno" required><br>
<input name="age" type="number" required><br>
<input name="level" placeholder="Úroveň" required><br>
<input name="available_time" type="datetime-local" required><br>
<input name="email" required><br>
<button>Uložit</button>
</form>

<h2>Hráči:</h2>
<ul>
{% for p in players %}
<li>{{ p[1] }} - {{ p[2] }}</li>
{% endfor %}
</ul>
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

@app.route("/", methods=["GET","POST"])
def home():
    if request.method == "POST":
        data = request.form

        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
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
        conn.commit()
        conn.close()

    return render_template_string(HTML, players=get_players())

@app.route("/ping")
def ping():
    return "pong"

# 🔥 důležité
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
