import time
import statistics
import pandas as pd
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# =========================
# CONFIG (ENV)
# =========================

TOKEN = "8750698916:AAEgYA-AQqienTfKYd8GzGTBj7ypjrPz_UM"
CHAT_ID = "5019372975"

BASE_BALANCE = 100
balance_sim = BASE_BALANCE

HISTORY_LIMIT = 300

# =========================
# SELENIUM HEADLESS
# =========================

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)
driver.get("https://stake.com/casino/games/aviator")

print("Esperando carga...")

time.sleep(15)

# =========================
# VARIABLES
# =========================

history = []
signals_log = []

strategies = [
    {"name": "safe", "target": 1.5, "risk": 0.01},
    {"name": "balanced", "target": 1.7, "risk": 0.02},
    {"name": "aggressive", "target": 2.0, "risk": 0.03},
]

strategy_stats = {
    s["name"]: {"wins": 0, "losses": 0, "profit": 0}
    for s in strategies
}

# =========================
# TELEGRAM
# =========================

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

# =========================
# SCRAPER
# =========================

def get_last_result():
    try:
        element = driver.find_element(By.CLASS_NAME, "payouts-block")
        text = element.text.split("\n")[0]
        return float(text.replace("x", ""))
    except:
        return None

# =========================
# ESTRATEGIAS
# =========================

def simulate_all(result):
    global balance_sim

    for s in strategies:
        name = s["name"]
        target = s["target"]
        risk = s["risk"]

        bet = balance_sim * risk

        if result >= target:
            profit = bet * (target - 1)
            strategy_stats[name]["wins"] += 1
        else:
            profit = -bet
            strategy_stats[name]["losses"] += 1

        strategy_stats[name]["profit"] += profit

def select_best():
    best = None
    best_score = -999

    for name, stats in strategy_stats.items():
        total = stats["wins"] + stats["losses"]

        if total < 15:
            continue

        winrate = stats["wins"] / total
        score = stats["profit"] + (winrate * 10)

        if score > best_score:
            best_score = score
            best = name

    return best

def get_config(name):
    for s in strategies:
        if s["name"] == name:
            return s

# =========================
# DASHBOARD
# =========================

def dashboard():
    df = pd.DataFrame(signals_log)

    if df.empty:
        return

    wins = (df["outcome"] == "WIN").sum()
    total = len(df)

    winrate = wins / total * 100
    profit = balance_sim - BASE_BALANCE

    print(f"📊 Señales: {total} | Winrate: {winrate:.2f}% | Profit: {profit:.2f}")

    df.to_csv("reporte.csv", index=False)

# =========================
# LOOP
# =========================

last = None

while True:

    result = get_last_result()

    if not result or result == last:
        continue

    last = result

    history.append(result)

    if len(history) > HISTORY_LIMIT:
        history.pop(0)

    print(f"🎲 {result}x")

    simulate_all(result)

    best = select_best()

    if best:
        config = get_config(best)

        signal_msg = f"🚀 ENTRAR\nTarget: {config['target']}x\nModo: {best.upper()}"
        print(signal_msg)

        send_telegram(signal_msg)

        # simulación real
        bet = balance_sim * config["risk"]

        if result >= config["target"]:
            balance_sim += bet * (config["target"] - 1)
            outcome = "WIN"
        else:
            balance_sim -= bet
            outcome = "LOSS"

        signals_log.append({
            "time": datetime.now(),
            "result": result,
            "target": config["target"],
            "outcome": outcome,
            "balance": balance_sim
        })

    dashboard()

    time.sleep(1)
