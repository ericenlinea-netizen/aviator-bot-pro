from flask import Flask, request
import pandas as pd
import requests
from datetime import datetime

app = Flask(__name__)

# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN = "TU_TOKEN"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"

balance = 100

history = []
signals_log = []

strategies = [
    {"name": "safe", "target": 1.5, "risk": 0.01},
    {"name": "balanced", "target": 1.7, "risk": 0.02},
    {"name": "aggressive", "target": 2.0, "risk": 0.03},
]

stats = {s["name"]: {"wins": 0, "losses": 0, "profit": 0} for s in strategies}

# =========================
# TELEGRAM
# =========================

def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

# =========================
# LOGICA
# =========================

def simulate_all(result):
    global balance

    for s in strategies:
        name = s["name"]
        bet = balance * s["risk"]

        if result >= s["target"]:
            profit = bet * (s["target"] - 1)
            stats[name]["wins"] += 1
        else:
            profit = -bet
            stats[name]["losses"] += 1

        stats[name]["profit"] += profit

def best_strategy():
    best = None
    best_score = -999

    for name, s in stats.items():
        total = s["wins"] + s["losses"]

        if total < 10:
            continue

        winrate = s["wins"] / total
        score = s["profit"] + winrate * 10

        if score > best_score:
            best_score = score
            best = name

    return best

# =========================
# ENDPOINT
# =========================

@app.route("/data", methods=["POST"])
def data():
    global balance

    result = request.json["result"]

    print(f"🎲 {result}")

    history.append(result)

    simulate_all(result)

    best = best_strategy()

    if best:
        config = next(s for s in strategies if s["name"] == best)

        msg = f"🚀 ENTRAR\nTarget: {config['target']}x\nModo: {best.upper()}"
        print(msg)
        send(msg)

        bet = balance * config["risk"]

        if result >= config["target"]:
            balance += bet * (config["target"] - 1)
            outcome = "WIN"
        else:
            balance -= bet
            outcome = "LOSS"

        signals_log.append({
            "time": str(datetime.now()),
            "result": result,
            "strategy": best,
            "balance": balance
        })

    return {"status": "ok"}

# =========================
# RUN
# =========================

app.run(host="0.0.0.0", port=8080)
