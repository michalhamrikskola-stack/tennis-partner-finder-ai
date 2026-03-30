
Hamřa
9:58 (před 0 minutami)
komu: mně

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

HTML = "<h1>Tennis Partner Finder AI běží 🚀</h1>"

def get_conn():
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
return conn

def init_db():
conn = get_conn()
conn.execute("""
CREATE TABLE IF NOT EXISTS players (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nickname TEXT,
city TEXT,
age INTEGER,
level TEXT,
available_time TEXT,
email TEXT,
created_at TEXT
)
""")
conn.commit()
conn.close()

def find_match_for_player(player):
conn = get_conn()
candidates = conn.execute("""
SELECT * FROM players
WHERE id != ? AND city = ? AND level = ?
""", (player["id"], player["city"], player["level"])).fetchall()
conn.close()

player_time = datetime.datetime.strptime(player["available_time"], "%Y-%m-%dT%H:%M")

for candidate in candidates:
candidate_time = datetime.datetime.strptime(candidate["available_time"], "%Y-%m-%dT%H:%M")
diff = abs((candidate_time - player_time).total_seconds()) / 60
if diff <= 60:
return candidate, int(diff)

return None, None

def ai_match_message(player, match, diff_minutes):
if not OPENAI_API_KEY:
return "AI není nastavená."

try:
prompt = "Najdi tenisového spoluhráče."

response = requests.post(
f"{OPENAI_BASE_URL}/chat/completions",
headers={
"Authorization": f"Bearer {OPENAI_API_KEY}",
"Content-Type": "application/json",
},
json={
"model": OPENAI_MODEL,
"messages": [{"role": "user", "content": prompt}],
},
timeout=30
)

data = response.json()
return data["choices"][0]["message"]["content"]

except Exception as e:
return f"AI chyba: {str(e)}"

@app.route("/")
def home():
return HTML

@app.route("/ping")
def ping():
return "pong"

@app.route("/status")
def status():
return jsonify({"status": "ok"})

@app.route("/player", methods=["POST"])
def add_player():
data = request.get_json()

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
message = ai_match_message(player, match, diff)

return jsonify({"message": message})

if __name__ == "__main__":
init_db()
app.run(host="0.0.0.0", port=8081)
