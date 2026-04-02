import time
import statistics
import pandas as pd
import requests
import os
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# =========================
# CONFIG (ENV)
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_BALANCE = 100
balance_sim = BASE_BALANCE

HISTORY_LIMIT = 300

# =========================
# SELENIUM (HEADLESS)
# =========================

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

print("🌐 Iniciando navegador...")

driver = webdriver.Chrome(options=options)

driver.get("https://stake.com/casino/games/aviator")

print("⏳ Esperando carga...")
time.sleep(20)

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

last_result_seen = None

# =========================
# TELEGRAM
# =========================

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram no configurado")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        })
    except Exception as e:
        print("⚠️ Error Telegram:", e)

# =========================
# SCRAPER (ROBUSTO)
# =========================

def get_last_result():
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "[class*=payout]")

        for el in elements:
            text = el.text.replace("x", "").strip()

            try:
                value = float(text)
                if value > 1:
                    return value
            except:
                continue

        return None

    except Exception as e:
        print("Error scraping:", e)
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

        if total < 20:
            continue

        winrate = stats["wins"] / total
        profit = stats["profit"]

        score = profit + (winrate * 10)

        if score > best_score:
            best_score = score
            best = name

    return best

def get_strategy(name):
    for s in strategies:
        if s["name"] == name:
            return s
    return None

# =========================
# DASHBOARD
# =========================

def dashboard():
    if not signals_log:
        return

    df = pd.DataFrame(signals_log)

    wins = (df["outcome"] == "WIN").sum()
    total = len(df)

    winrate = (wins / total) * 100
    profit = balance_sim - BASE_BALANCE

    print("\n📊 ===== DASHBOARD =====")
    print(f"Señales: {total}")
    print(f"Winrate: {winrate:.2f}%")
    print(f"Profit: {profit:.2f}")
    print("=======================\n")

    df.to_csv("reporte.csv", index=False)

# =========================
# LOOP PRINCIPAL
# =========================

print("🚀 Bot iniciado...")

while True:

    try:
        result = get_last_result()

        if result is None:
            time.sleep(1)
            continue

        if result == last_result_seen:
            time.sleep(0.5)
            continue

        last_result_seen = result

        print(f"🎲 Resultado: {result}x")

        history.append(result)

        if len(history) > HISTORY_LIMIT:
            history.pop(0)

        # 🔥 entrenar estrategias
        simulate_all(result)

        # 🧠 seleccionar mejor estrategia
        best = select_best()

        if best:
            config = get_strategy(best)

            signal_msg = (
                f"🚀 ENTRAR\n"
                f"Target: {config['target']}x\n"
                f"Modo: {best.upper()}"
            )

            print(signal_msg)
            send_telegram(signal_msg)

            # 💰 simulación
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

    except Exception as e:
        print("⚠️ Error en loop:", e)
        time.sleep(2)
