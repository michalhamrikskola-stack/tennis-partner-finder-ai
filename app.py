from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import datetime
import requests

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "players.db")
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
        :root {
            --bg: #f4f7fb;
            --card: #ffffff;
            --text: #1d2733;
            --muted: #5f6b7a;
            --line: #d9e2ec;
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --success-bg: #e8f7ee;
            --success-text: #196c3b;
            --warn-bg: #fff4e5;
            --warn-text: #9a5a00;
            --shadow: 0 12px 28px rgba(17, 24, 39, 0.08);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background:
                radial-gradient(circle at top left, #e8f1ff 0%, transparent 30%),
                radial-gradient(circle at top right, #e9fff2 0%, transparent 25%),
                var(--bg);
            color: var(--text);
        }

        .container {
            max-width: 1180px;
            margin: 0 auto;
            padding: 24px;
        }

        .hero {
            background: linear-gradient(135deg, #0f172a, #1e3a8a);
            color: white;
            border-radius: 24px;
            padding: 28px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
        }

        .hero h1 {
            margin: 0 0 12px 0;
            font-size: 34px;
        }

        .hero p {
            margin: 0;
            line-height: 1.6;
            color: #e5ecff;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 1.3fr 1fr;
            gap: 22px;
            align-items: start;
        }

        .chip {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: rgba(255,255,255,0.12);
            margin: 6px 6px 0 0;
            font-size: 13px;
        }

        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .card {
            background: var(--card);
            border-radius: 22px;
            padding: 22px;
            box-shadow: var(--shadow);
            margin-bottom: 24px;
        }

        h2, h3 {
            margin-top: 0;
        }

        .muted {
            color: var(--muted);
            line-height: 1.6;
        }

        label {
            display: block;
            margin: 14px 0 7px;
            font-weight: 700;
            color: #243243;
        }

        input, select, textarea, button {
            width: 100%;
            border-radius: 14px;
            border: 1px solid var(--line);
            padding: 13px 14px;
            font-size: 15px;
        }

        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.10);
        }

        button {
            margin-top: 18px;
            background: var(--primary);
            color: white;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: 0.2s ease;
        }

        button:hover {
            background: var(--primary-dark);
            transform: translateY(-1px);
        }

        .message-success {
            background: var(--success-bg);
            color: var(--success-text);
            padding: 12px 14px;
            border-radius: 14px;
            margin-bottom: 16px;
        }

        .message-error {
            background: #fdeaea;
            color: #9f2b2b;
            padding: 12px 14px;
            border-radius: 14px;
            margin-bottom: 16px;
            white-space: pre-wrap;
        }

        .matchbox {
            min-height: 290px;
            background: #f8fbff;
            resize: vertical;
            line-height: 1.55;
        }

        .tip {
            background: var(--warn-bg);
            color: var(--warn-text);
            border-radius: 14px;
            padding: 12px 14px;
            margin-top: 14px;
            line-height: 1.5;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            overflow: hidden;
            border-radius: 16px;
        }

        th, td {
            padding: 14px 12px;
            border-bottom: 1px solid #edf2f7;
            text-align: left;
            vertical-align: top;
            font-size: 14px;
        }

        th {
            background: #f8fbff;
            color: #334155;
        }

        tr:hover td {
            background: #fbfdff;
        }

        .city-pill {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #eef4ff;
            color: #2348a5;
            font-size: 12px;
            font-weight: 700;
        }

        .footer-note {
            font-size: 13px;
            color: var(--muted);
            margin-top: 10px;
        }

        @media (max-width: 950px) {
            .grid, .hero-grid {
                grid-template-columns: 1fr;
            }

            .container {
                padding: 14px;
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
        <div class="hero-grid">
            <div>
                <h1>🎾 Tennis Partner Finder AI</h1>
                <p>
                    Webová aplikace pro hledání spoluhráče na tenis. Vyplníš formulář,
                    profil se uloží do databáze a systém s pomocí AI zjistí, jestli už
                    v aplikaci existuje vhodná shoda podle <strong>města</strong>,
                    <strong>úrovně</strong> a <strong>času v rozmezí ± 60 minut</strong>.
                </p>
                <div style="margin-top: 14px;">
                    <span class="chip">Praha / Brno</span>
                    <span class="chip">Úroveň hráče</span>
                    <span class="chip">Kalendář + čas</span>
                    <span class="chip">AI odpověď</span>
                    <span class="chip">GDPR-friendly</span>
                </div>
            </div>
            <div>
                <h3>Jak to funguje</h3>
                <p class="muted">
                    1. Vyplníš přezdívku, město, věk, úroveň, termín a e-mail.<br>
                    2. Hráč se uloží do databáze.<br>
                    3. Systém hledá stejnou úroveň, stejné město a podobný čas.<br>
                    4. AI napíše, jestli našla spoluhráče, nebo ne.
                </p>
            </div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Nový hráč</h2>
            <p class="muted">
                Kvůli soukromí zadávej jen křestní jméno nebo přezdívku, ne celé jméno a příjmení.
            </p>

            {% if message %}<div class="message-success">{{ message }}</div>{% endif %}
            {% if error %}<div class="message-error">{{ error }}</div>{% endif %}

            <form method="post" action="/player-form">
                <label for="nickname">Jméno nebo přezdívka</label>
                <input id="nickname" name="nickname" required maxlength="40" placeholder="Např. Michal nebo Misa23">

                <label for="city">Město</label>
                <select id="city" name="city" required>
                    <option value="">Vyber město</option>
                    <option value="Praha">Praha</option>
                    <option value="Brno">Brno</option>
                </select>

                <label for="age">Věk</label>
                <input id="age" name="age" type="number" min="10" max="99" required placeholder="Např. 21">

                <label for="level">Úroveň</label>
                <select id="level" name="level" required>
                    <option value="">Vyber úroveň</option>
                    <option value="začátečník">Začátečník</option>
                    <option value="středně pokročilý">Středně pokročilý</option>
                    <option value="pokročilý">Pokročilý</option>
                    <option value="profesionál">Profesionál</option>
                </select>

                <label for="available_time">Kdy může hrát</label>
                <input id="available_time" name="available_time" type="datetime-local" required>

                <label for="email">E-mail</label>
                <input id="email" name="email" type="email" required placeholder="napr. michal@email.cz">

                <button type="submit">Uložit hráče</button>
            </form>

            <div class="tip">
                Tip: Pro otestování shody přidej dva hráče se stejným městem, stejnou úrovní
                a časem například 18:00 a 18:30.
            </div>
        </div>

        <div class="card">
            <h2>AI odpověď</h2>
            <textarea class="matchbox" readonly>{{ match_message or "Po uložení hráče se zde zobrazí odpověď AI. Když systém nikoho nenajde, napíše, že aktuálně nemá nikdo zájem o hru ve stejný čas." }}</textarea>
            <p class="footer-note">
                Plný kontakt se zobrazí jen tehdy, když systém najde vhodného spoluhráče.
            </p>
        </div>
    </div>

    <div class="card">
        <h2>Soukromí a zobrazení dat</h2>
        <p class="muted">
            Ve veřejném seznamu se zobrazuje pouze přezdívka, město, věk, úroveň, termín a
            <strong>maskovaný e-mail</strong>. Plný e-mail se ukazuje jen ve výsledku nalezené shody.
        </p>
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
                    <th>Kdy může hrát</th>
                    <th>Kontakt</th>
                </tr>
            </thead>
            <tbody>
                {% for p in players %}
                <tr>
                    <td>{{ p["id"] }}</td>
                    <td>{{ p["nickname"] }}</td>
                    <td><span class="city-pill">{{ p["city"] }}</span></td>
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

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            city TEXT NOT NULL,
            age INTEGER NOT NULL,
            level TEXT NOT NULL,
            available_time TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def mask_email(email):
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = (local[:1] or "*") + "*"
    else:
        masked_local = local[:2] + "*" * max(1, len(local) - 2)
    return masked_local + "@" + domain

def fetch_players():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM players ORDER BY id DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["masked_email"] = mask_email(d["email"])
        result.append(d)
    return result

def validate_payload(data):
    required = ["nickname", "city", "age", "level", "available_time", "email"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        return "Chybí pole: " + ", ".join(missing)

    if data["city"] not in ["Praha", "Brno"]:
        return "Město musí být Praha nebo Brno."

    if data["level"] not in ["začátečník", "středně pokročilý", "pokročilý", "profesionál"]:
        return "Neplatná úroveň."

    try:
        age = int(data["age"])
        if age < 10 or age > 99:
            return "Věk musí být mezi 10 a 99."
    except Exception:
        return "Věk musí být číslo."

    try:
        datetime.datetime.strptime(data["available_time"], "%Y-%m-%dT%H:%M")
    except Exception:
        return "Termín musí být ve formátu datum a čas."

    return None

def find_match_for_player(player):
    conn = get_conn()
    candidates = conn.execute("""
        SELECT * FROM players
        WHERE id != ? AND city = ? AND level = ?
    """, (player["id"], player["city"], player["level"])).fetchall()
    conn.close()

    player_time = datetime.datetime.strptime(player["available_time"], "%Y-%m-%dT%H:%M")
    best_match = None
    best_diff = None

    for candidate in candidates:
        candidate_time = datetime.datetime.strptime(candidate["available_time"], "%Y-%m-%dT%H:%M")
        diff_minutes = int(abs((candidate_time - player_time).total_seconds()) / 60)
        if diff_minutes <= 60:
            if best_diff is None or diff_minutes < best_diff:
                best_match = candidate
                best_diff = diff_minutes

    return best_match, best_diff

def local_match_message(match, diff_minutes):
    if not match:
        return "Aktuálně nemá nikdo zájem o hru ve stejný čas. Zkus to později nebo uprav čas."

    match_dt = datetime.datetime.strptime(match["available_time"], "%Y-%m-%dT%H:%M")
    date_str = match_dt.strftime("%d.%m.%Y")
    time_str = match_dt.strftime("%H:%M")

    if diff_minutes == 0:
        time_info = "Má zájem ve stejný den a stejnou hodinu."
    else:
        time_info = f"Čas se liší o {diff_minutes} minut, ale stále se dobře shodujete."

    return (
        f"Našel jsem ti spoluhráče!\n\n"
        f"Přezdívka: {match['nickname']}\n"
        f"Město: {match['city']}\n"
        f"Datum: {date_str}\n"
        f"Hodina: {time_str}\n"
        f"Úroveň: {match['level']}\n"
        f"Věk: {match['age']}\n"
        f"E-mail pro kontakt: {match['email']}\n\n"
        f"{time_info}"
    )

def ai_match_message(player, match, diff_minutes):
    if not OPENAI_API_KEY:
        return local_match_message(match, diff_minutes)

    if not match:
        prompt = f"""
Napiš krátkou odpověď v češtině pro tenisovou aplikaci.
Uživatel:
- přezdívka: {player['nickname']}
- město: {player['city']}
- úroveň: {player['level']}
- věk: {player['age']}
- termín: {player['available_time']}

Výsledek: nebyl nalezen žádný vhodný spoluhráč.
Pravidla:
- napiš maximálně 2 krátké věty
- použij přátelský styl
- napiš, že aktuálně nemá nikdo zájem o hru ve stejný čas
- nepiš nic navíc
""".strip()
    else:
        prompt = f"""
Napiš krátkou odpověď v češtině pro tenisovou aplikaci.
Uživatel:
- přezdívka: {player['nickname']}
- město: {player['city']}
- úroveň: {player['level']}
- věk: {player['age']}
- termín: {player['available_time']}

Nalezený spoluhráč:
- přezdívka: {match['nickname']}
- město: {match['city']}
- úroveň: {match['level']}
- věk: {match['age']}
- termín: {match['available_time']}
- email: {match['email']}
- rozdíl času v minutách: {diff_minutes}

Pravidla:
- začni větou "Našel jsem ti spoluhráče!"
- uveď datum, hodinu, úroveň, věk a email
- pokud je rozdíl času 0, napiš že má zájem ve stejný den a stejnou hodinu
- pokud je rozdíl jiný, napiš že se čas liší o daný počet minut
- piš přehledně po krátkých řádcích
""".strip()

    try:
        response = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=60,
            verify=False,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return local_match_message(match, diff_minutes)

init_db()

@app.route("/")
def home():
    return render_template_string(
        HTML,
        players=fetch_players(),
        message=None,
        error=None,
        match_message=None
    )

@app.route("/ping")
def ping():
    return "pong"

@app.route("/status")
def status():
    return jsonify({
        "status": "ok",
        "author": "Michal Hamřík",
        "time": str(datetime.datetime.now()),
        "model": OPENAI_MODEL,
        "base_url": OPENAI_BASE_URL
    })

@app.route("/players")
def players():
    return jsonify(fetch_players())

@app.route("/player", methods=["POST"])
def add_player_api():
    data = request.get_json(silent=True) or {}
    error = validate_payload(data)
    if error:
        return jsonify({"error": error}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO players (nickname, city, age, level, available_time, email, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nickname"].strip(),
        data["city"],
        int(data["age"]),
        data["level"],
        data["available_time"],
        data["email"].strip(),
        str(datetime.datetime.now())
    ))
    player_id = cursor.lastrowid
    conn.commit()
    player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    conn.close()

    match, diff = find_match_for_player(player)
    match_message = ai_match_message(player, match, diff)

    return jsonify({
        "message": "player added",
        "match_message": match_message
    }), 201

@app.route("/player-form", methods=["POST"])
def add_player_form():
    data = {
        "nickname": request.form.get("nickname", "").strip(),
        "city": request.form.get("city", "").strip(),
        "age": request.form.get("age", "").strip(),
        "level": request.form.get("level", "").strip(),
        "available_time": request.form.get("available_time", "").strip(),
        "email": request.form.get("email", "").strip(),
    }

    error = validate_payload(data)
    if error:
        return render_template_string(
            HTML,
            players=fetch_players(),
            message=None,
            error=error,
            match_message=None
        ), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO players (nickname, city, age, level, available_time, email, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nickname"],
        data["city"],
        int(data["age"]),
        data["level"],
        data["available_time"],
        data["email"],
        str(datetime.datetime.now())
    ))
    player_id = cursor.lastrowid
    conn.commit()
    player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    conn.close()

    match, diff = find_match_for_player(player)
    match_message = ai_match_message(player, match, diff)

    return render_template_string(
        HTML,
        players=fetch_players(),
        message="Hráč byl úspěšně uložen.",
        error=None,
        match_message=match_message
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8081)))
