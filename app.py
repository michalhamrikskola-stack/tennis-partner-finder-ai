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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Tennis Partner Finder AI</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f4f7fb;
            color: #1d2733;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 24px;
        }

        .hero {
            background: linear-gradient(135deg, #0f172a, #1e3a8a);
            color: white;
            border-radius: 22px;
            padding: 26px;
            margin-bottom: 24px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.10);
        }

        .hero h1 {
            margin: 0 0 10px 0;
            font-size: 34px;
        }

        .hero p {
            margin: 0;
            line-height: 1.6;
            color: #e5ecff;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 22px;
        }

        .card {
            background: white;
            border-radius: 18px;
            padding: 20px;
            box-shadow: 0 10px 24px rgba(0,0,0,0.08);
            margin-bottom: 22px;
        }

        h2 {
            margin-top: 0;
        }

        label {
            display: block;
            margin: 12px 0 6px;
            font-weight: bold;
        }

        input, select, textarea, button {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            border: 1px solid #cfd8e3;
            border-radius: 10px;
            font-size: 14px;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
        }

        button {
            margin-top: 16px;
            background: #2563eb;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
        }

        button:hover {
            background: #1d4ed8;
        }

        textarea {
            min-height: 260px;
            resize: vertical;
            background: #f8fbff;
            line-height: 1.5;
        }

        .success {
            background: #e8f7ee;
            color: #196c3b;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 16px;
        }

        .muted {
            color: #5f6b7a;
            line-height: 1.6;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th, td {
            padding: 12px 10px;
            border-bottom: 1px solid #e6edf5;
            text-align: left;
            vertical-align: top;
        }

        th {
            background: #f8fbff;
        }

        .pill {
            display: inline-block;
            background: #eef4ff;
            color: #2348a5;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
        }

        @media (max-width: 900px) {
            .grid {
                grid-template-columns: 1fr;
            }

            .hero h1 {
                font-size: 28px;
            }
        }
    </style>
</head>
<body>
<div class="container">

    <div class="hero">
        <h1>🎾 Tennis Partner Finder AI</h1>
        <p>
            Vyplň formulář a aplikace najde vhodného spoluhráče podle města,
            úrovně a času v rozmezí ± 60 minut.
        </p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Nový hráč</h2>
            <p class="muted">
                Zadávej jen jméno nebo přezdívku. Kvůli soukromí se v seznamu zobrazuje maskovaný e-mail.
            </p>

            {% if message %}
                <div class="success">{{ message }}</div>
            {% endif %}

            <form method="post">
                <label for="nickname">Jméno nebo přezdívka</label>
                <input id="nickname" name="nickname" placeholder="Např. Marecek" required>

                <label for="city">Město</label>
                <select id="city" name="city" required>
                    <option value="">Vyber město</option>
                    <option value="Praha">Praha</option>
                    <option value="Brno">Brno</option>
                </select>

                <label for="age">Věk</label>
                <input id="age" name="age" type="number" placeholder="Např. 21" min="10" max="99" required>

                <label for="level">Úroveň</label>
                <select id="level" name="level" required>
                    <option value="">Vyber úroveň</option>
                    <option value="Začátečník">Začátečník</option>
                    <option value="Středně pokročilý">Středně pokročilý</option>
                    <option value="Pokročilý">Pokročilý</option>
                    <option value="Profesionál">Profesionál</option>
                </select>

                <label for="available_time">Kdy může hrát</label>
                <input id="available_time" name="available_time" type="datetime-local" required>

                <label for="email">E-mail</label>
                <input id="email" name="email" type="email" placeholder="napr. hrac@email.cz" required>

                <button type="submit">Uložit hráče</button>
            </form>
        </div>

        <div class="card">
            <h2>AI odpověď</h2>
            <textarea readonly>{{ match_message }}</textarea>
        </div>
    </div>

    <div class="card">
        <h2>Seznam hráčů</h2>
        {% if players %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Přezdívka</th>
                    <th>Město</th>
                    <th>Věk</th>
                    <th>Úroveň</th>
                    <th>Termín</th>
                    <th>Kontakt</th>
                </tr>
            </thead>
            <tbody>
                {% for p in players %}
                <tr>
                    <td>{{ p["id"] }}</td>
                    <td>{{ p["nickname"] }}</td>
                    <td><span class="pill">{{ p["city"] }}</span></td>
                    <td>{{ p["age"] }}</td>
                    <td>{{ p["level"] }}</td>
                    <td>{{ p["available_time"] }}</td>
                    <td>{{ p["masked_email"] }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
            <p class="muted">Zatím tu není žádný hráč.</p>
        {% endif %}
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

def mask_email(email):
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return (local[:1] or "*") + "*" + "@" + domain
    return local[:2] + "*" * (len(local) - 2) + "@" + domain

def fetch_players():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM players ORDER BY id DESC").fetchall()
    conn.close()

    result = []
    for row in rows:
        item = dict(row)
        item["masked_email"] = mask_email(item["email"])
        result.append(item)
    return result

def find_match(player):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM players
        WHERE id != ? AND city = ? AND level = ?
    """, (player["id"], player["city"], player["level"])).fetchall()
    conn.close()

    player_time = datetime.datetime.fromisoformat(player["available_time"])
    best_match = None
    best_diff = None

    for row in rows:
        candidate_time = datetime.datetime.fromisoformat(row["available_time"])
        diff = int(abs((candidate_time - player_time).total_seconds()) / 60)

        if diff <= 60:
            if best_diff is None or diff < best_diff:
                best_match = row
                best_diff = diff

    return best_match, best_diff

def local_message(match, diff):
    if not match:
        return "Aktuálně nemá nikdo zájem o hru ve stejný čas. Zkus to později nebo uprav čas."

    dt = datetime.datetime.fromisoformat(match["available_time"])
    date_str = dt.strftime("%d.%m.%Y")
    time_str = dt.strftime("%H:%M")

    if diff == 0:
        time_info = "Má zájem ve stejný den a stejnou hodinu."
    else:
        time_info = f"Čas se liší o {diff} minut."

    return (
        f"Našel jsem ti spoluhráče!\n\n"
        f"Jméno: {match['nickname']}\n"
        f"Město: {match['city']}\n"
        f"Úroveň: {match['level']}\n"
        f"Věk: {match['age']}\n"
        f"Datum: {date_str}\n"
        f"Hodina: {time_str}\n"
        f"E-mail: {match['email']}\n\n"
        f"{time_info}"
    )

def ai_message(player, match, diff):
    if not OPENAI_API_KEY:
        return local_message(match, diff)

    if not match:
        prompt = (
            "Napiš krátkou odpověď v češtině pro tenisovou aplikaci. "
            "Aktuálně nebyl nalezen žádný spoluhráč ve stejný čas. "
            "Použij maximálně 2 krátké věty."
        )
    else:
        prompt = (
            f"Napiš krátkou odpověď v češtině pro tenisovou aplikaci.\n"
            f"Našel se spoluhráč {match['nickname']} z města {match['city']}.\n"
            f"Úroveň: {match['level']}, věk: {match['age']}, email: {match['email']}.\n"
            f"Termín: {match['available_time']}. Rozdíl času: {diff} minut.\n"
            f"Začni větou: Našel jsem ti spoluhráče!"
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
                "temperature": 0.2
            },
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return local_message(match, diff)

@app.route("/", methods=["GET", "POST"])
def home():
    message = None
    match_message = "Po uložení hráče se zde zobrazí odpověď."

    if request.method == "POST":
        data = request.form

        conn = get_conn()
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
        player_id = cursor.lastrowid
        conn.commit()

        player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        conn.close()

        match, diff = find_match(player)
        match_message = ai_message(player, match, diff)
        message = "Hráč byl úspěšně uložen."

    return render_template_string(
        HTML,
        players=fetch_players(),
        message=message,
        match_message=match_message
    )

@app.route("/ping")
def ping():
    return "pong"

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
