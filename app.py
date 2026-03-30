from flask import Flask
import sqlite3
import os

app = Flask(__name__)

# 🔥 NATVRDO /tmp (jediné co tam funguje)
DB_PATH = "/tmp/players.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
    conn.commit()
    conn.close()

@app.route("/")
def home():
    return "APP JEDE"

@app.route("/ping")
def ping():
    return "pong"

# 🔥 INIT AŽ PO DEFINICI FUNKCÍ
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
