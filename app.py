from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
import datetime
import requests

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "players.db")
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
.card {
background: white;
border-radius: 18px;
padding: 20px;
margin-bottom: 20px;
box-shadow: 0 10px 24px rgba(0,0,0,0.08);
}
h1, h2 {
margin-top: 0;
}
.grid {
display: grid;
grid-template-columns: 1fr 1fr;
gap: 20px;
}
label {
display: block;
margin: 12px 0 6px;
font-weight: bold;
}
input, select, textarea, button {
width: 100%;
padding: 12px;
border-radius: 10px;
border: 1px solid #cfd8e3;
box-sizing: border-box;
font-size: 14px;
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
.success {
background: #e8f7ee;
color: #196c3b;
padding: 12px;
border-radius: 10px;
margin-bottom: 16px;
}
.error {
background: #fdeaea;
color: #9f2b2b;
padding: 12px;
border-radius: 10px;
margin-bottom: 16px;
white-space: pre-wrap;
}
.matchbox {
min-height: 260px;
background: #f8fbff;
resize: vertical;
}
table {
width: 100%;
border-collapse: collapse;
}
th, td {
border-bottom: 1px solid #e6edf5;
padding: 12px 10px;
text-align: left;
vertical-align: top;
}
th {
background: #f8fbff;
}
.muted {
color: #5f6b7a;
}
@media (max-width: 900px) {
.grid {
grid-template-columns: 1fr;
}
}
</style>
</head>
<body>
<div class="container">
<div class="card">
<h1>🎾 Tennis Partner Finder AI</h1>
<p class="muted">
Vyplň formulář a systém zkusí najít spoluhráče podle města, úrovně a času v rozmezí ± 60 minut.
</p>
</div>

<div class="grid">
<div class="card">
<h2>Nový hráč</h2>

{% if message %}
<div class="success">{{ message }}</div>
{% endif %}

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

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
</div>

<div class="card">
<h2>AI odpověď</h2>
<textarea class="matchbox" readonly>{{ match_message or "Po uložení hráče se zde zobrazí odpověď." }}</textarea>
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
<th>Kdy může hrát</th>
<th>Kontakt</th>
</tr>
</thead>
<tbody>
{% for p in players %}
<tr>
<td>{{ p["id"] }}</td>
<td>{{ p["nickname"] }}</td>
<td>{{ p["city"] }}</td>
<td>{{ p["age"] }}</td>
<td>{{ p["level"] }}</td>
<td>{{ p["available_time"] }}</td>
<td>{{ p["masked_email"] }}</td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<p>Zatím tu není žádný hráč.</p>
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
item = dict(row)
item["masked_email"] = mask_email(item["email"])
result.append(item)
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
timeout=15
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
"model": OPENAI_MODEL
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
app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
