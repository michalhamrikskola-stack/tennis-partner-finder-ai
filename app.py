# Importuje třídu Flask pro vytvoření webové aplikace,
# request pro práci s daty z formuláře
# a render_template_string pro vykreslení HTML šablony uložené v proměnné.
from flask import Flask, request, render_template_string

# Importuje sqlite3 pro práci s SQLite databází.
import sqlite3

# Importuje datetime pro práci s datem a časem.
import datetime

# Vytvoří instanci Flask aplikace.
app = Flask(__name__)

# Cesta k databázovému souboru.
DB_PATH = "/data/players.db"

# HTML šablona celé stránky jako víceřádkový text.
HTML = """
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tennis Partner Finder AI</title>

<style>
/* Nastavení základního vzhledu celé stránky */
body { margin:0; font-family:Arial; background:#f4f7fb; }

/* Hlavní kontejner stránky */
.container { max-width:1100px; margin:auto; padding:20px; }

/* Horní úvodní část stránky */
.hero {
    background:linear-gradient(135deg,#0f172a,#1e3a8a);
    color:white;
    border-radius:20px;
    padding:25px;
    margin-bottom:20px;
}

/* Dvousloupcové rozložení */
.grid {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:20px;
}

/* Karta s bílým pozadím */
.card {
    background:white;
    border-radius:18px;
    padding:20px;
    box-shadow:0 10px 25px rgba(0,0,0,0.08);
}

/* Styl formulářových prvků */
input, select, textarea {
    width:100%;
    padding:12px;
    margin-top:5px;
    border-radius:10px;
    border:1px solid #ccc;
    box-sizing:border-box;
}

/* Styl tlačítka */
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

/* Výška textového pole */
textarea { height:250px; }

/* Styl jednoho hráče ve výpisu */
.player {
    padding:10px;
    border-bottom:1px solid #eee;
}

/* Zpráva o úspěchu */
.success {
    background:#e8f7ee;
    color:#196c3b;
    padding:10px;
    border-radius:10px;
    margin-bottom:10px;
}

/* Pro menší obrazovky přepne grid na jeden sloupec */
@media(max-width:900px){
    .grid{grid-template-columns:1fr;}
}
</style>
</head>

<body>
<div class="container">

<!-- Horní nadpis -->
<div class="hero">
<h1>🎾 Tennis Partner Finder AI</h1>
<p>Najdi spoluhráče podle města, úrovně a času</p>
</div>

<div class="grid">

<!-- Levá karta s formulářem -->
<div class="card">
{% if message %}
<!-- Pokud existuje zpráva, zobrazí se -->
<div class="success">{{ message }}</div>
{% endif %}

<form method="post">

<!-- Pole pro jméno hráče -->
<input name="nickname" placeholder="Jméno" required>

<!-- Výběr města -->
<select name="city" required>
<option value="">Město</option>
<option>Praha</option>
<option>Brno</option>
</select>

<!-- Věk hráče -->
<input name="age" type="number" placeholder="Věk" required>

<!-- Úroveň hráče -->
<select name="level" required>
<option value="">Úroveň</option>
<option>Začátečník</option>
<option>Středně pokročilý</option>
<option>Pokročilý</option>
<option>Profesionál</option>
</select>

<!-- Dostupný čas -->
<input name="available_time" type="datetime-local" required>

<!-- Email hráče -->
<input name="email" placeholder="Email" required>

<!-- Odeslání formuláře -->
<button>Uložit</button>
</form>
</div>

<!-- Pravá karta s výsledkem AI -->
<div class="card">
<h2>AI odpověď</h2>
<textarea readonly>{{ match_message }}</textarea>
</div>

</div>

<!-- Karta s výpisem všech hráčů -->
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

# Funkce pro vytvoření databáze a tabulky, pokud ještě neexistují.
def init_db():
    # Připojí se k databázi.
    conn = sqlite3.connect(DB_PATH)

    # Vytvoří tabulku players, pokud ještě neexistuje.
    conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,   -- Unikátní ID hráče
        nickname TEXT,                          -- Jméno / přezdívka
        city TEXT,                              -- Město
        age INTEGER,                            -- Věk
        level TEXT,                             -- Úroveň hráče
        available_time TEXT,                    -- Dostupný čas
        email TEXT                              -- Email
    )
    """)

    # Uloží změny.
    conn.commit()

    # Zavře spojení.
    conn.close()

# Funkce pro otevření spojení s databází.
def get_conn():
    # Připojí se k databázi.
    conn = sqlite3.connect(DB_PATH)

    # Nastaví, aby se řádky vracely jako slovník/přístup přes názvy sloupců.
    conn.row_factory = sqlite3.Row

    # Vrátí spojení.
    return conn

# Funkce načte všechny hráče z databáze.
def fetch_players():
    # Otevře spojení.
    conn = get_conn()

    # Načte všechny hráče seřazené od nejnovějších.
    rows = conn.execute("SELECT * FROM players ORDER BY id DESC").fetchall()

    # Zavře spojení.
    conn.close()

    # Převede výsledky na seznam slovníků.
    return [dict(r) for r in rows]

# Funkce hledá vhodného spoluhráče pro právě vloženého hráče.
def find_match(player):
    # Otevře spojení.
    conn = get_conn()

    # Najde hráče:
    # - kteří nejsou tento aktuální hráč
    # - mají stejné město
    # - mají stejnou úroveň
    rows = conn.execute("""
    SELECT * FROM players
    WHERE id != ? AND city = ? AND level = ?
    """, (player["id"], player["city"], player["level"])).fetchall()

    # Zavře spojení.
    conn.close()

    # Převede čas aktuálního hráče z textu na datetime objekt.
    player_time = datetime.datetime.fromisoformat(player["available_time"])

    # Projde nalezené hráče.
    for r in rows:
        # Převede čas nalezeného hráče na datetime.
        t = datetime.datetime.fromisoformat(r["available_time"])

        # Spočítá rozdíl času v minutách.
        diff = int(abs((t - player_time).total_seconds()) / 60)

        # Pokud je rozdíl nejvýše 60 minut, vrátí tohoto hráče a rozdíl.
        if diff <= 60:
            return r, diff

    # Pokud nikoho nenašel, vrátí None.
    return None, None

# Funkce vytvoří textovou odpověď pro uživatele.
def ai_match_message(player, match, diff):
    # Pokud nebyl nalezen spoluhráč.
    if not match:
        return (
            "V tuto chvíli nebyl nalezen žádný vhodný hráč ke hře.\n"
            "Zkuste upravit termín nebo to opakujte později."
        )

    # Převede čas nalezeného hráče na datetime.
    dt = datetime.datetime.fromisoformat(match["available_time"])

    # Naformátuje datum.
    date_str = dt.strftime("%d.%m.%Y")

    # Naformátuje čas.
    time_str = dt.strftime("%H:%M")

    # Pokud je čas úplně stejný.
    if diff == 0:
        time_text = "Váš čas se plně shoduje."
    else:
        # Jinak vypíše rozdíl v minutách.
        time_text = f"Čas se liší o {diff} minut."

    # Vrátí text výsledku.
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

# Definice hlavní stránky aplikace.
# Tato stránka reaguje na GET i POST.
@app.route("/", methods=["GET", "POST"])
def home():
    # Výchozí text v AI odpovědi.
    match_message = "Výsledek se zobrazí zde"

    # Výchozí zpráva o uložení je prázdná.
    message = None

    # Pokud byl formulář odeslán metodou POST.
    if request.method == "POST":
        # Načte odeslaná data z formuláře.
        d = request.form

        # Otevře spojení do databáze.
        conn = get_conn()
        cur = conn.cursor()

        # Vloží nového hráče do databáze.
        cur.execute("""
        INSERT INTO players (nickname, city, age, level, available_time, email)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d["nickname"],          # jméno
            d["city"],              # město
            int(d["age"]),          # věk převedený na číslo
            d["level"],             # úroveň
            d["available_time"],    # čas
            d["email"]              # email
        ))

        # Uloží ID právě vloženého hráče.
        pid = cur.lastrowid

        # Potvrdí změny v databázi.
        conn.commit()

        # Načte právě vloženého hráče podle ID.
        player = conn.execute("SELECT * FROM players WHERE id = ?", (pid,)).fetchone()

        # Zavře spojení.
        conn.close()

        # Najde vhodného spoluhráče.
        match, diff = find_match(player)

        # Vytvoří text výsledku.
        match_message = ai_match_message(player, match, diff)

        # Zpráva pro uživatele po uložení.
        message = "Hráč byl uložen."

    # Vrátí vykreslenou HTML stránku.
    return render_template_string(
        HTML,
        players=fetch_players(),       # seznam hráčů
        match_message=match_message,   # text AI odpovědi
        message=message                # potvrzovací zpráva
    )

# Jednoduchý testovací endpoint.
@app.route("/ping")
def ping():
    # Vrátí text pong.
    return "pong"

# Endpoint pro zobrazení celé databáze jako HTML.
@app.route("/db")
def show_db():
    # Připojí se přímo k databázi.
    conn = sqlite3.connect(DB_PATH)

    # Načte všechny řádky z tabulky players.
    rows = conn.execute("SELECT * FROM players").fetchall()

    # Zavře spojení.
    conn.close()

    # Začátek HTML výstupu.
    output = "<h1>Databáze hráčů</h1>"

    # Projde všechny řádky a přidá je do HTML.
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

    # Vrátí hotový HTML výstup.
    return output

# Zavolá inicializaci databáze při spuštění souboru.
init_db()

# Pokud je soubor spuštěn přímo, zapne Flask server.
if __name__ == "__main__":
    # Spustí aplikaci na všech síťových rozhraních na portu 8081.
    app.run(host="0.0.0.0", port=8081)
