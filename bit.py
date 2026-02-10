import os
import requests
import datetime
import time
import statistics

# ================= CONFIG =================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TRADING_START = 18  # 18h
TRADING_END = 22    # 22h
INTERVAL = 20       # secondes
# =========================================

prices = []
ao_history = []

# ================= DATA FETCH =================
def fetch_eurusd():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return float(data["price"])
    except Exception:
        return None

# ================= SIGNAL CALCULATIONS =================
def calculate_signal(prices):
    global ao_history
    if len(prices) < 34:
        return None, None

    sma20 = sum(prices[-20:]) / 20
    std20 = statistics.stdev(prices[-20:])
    upper = sma20 + 2 * std20
    lower = sma20 - 2 * std20

    last_five = prices[-6:-1]
    prev_avg = sum(last_five) / 5
    current = prices[-1]
    momentum = current - prev_avg

    sma5 = sum(prices[-5:]) / 5
    sma34 = sum(prices[-34:]) / 34
    ao = sma5 - sma34

    ao_history.append(ao)
    if len(ao_history) > 5:
        ao_history[:] = ao_history[-5:]

    ac = ao - (sum(ao_history) / 5) if len(ao_history) == 5 else 0

    signal = None
    if prev_avg < lower and momentum > 0 and ac > 0:
        signal = "buy"
    elif prev_avg > upper and momentum < 0 and ac < 0:
        signal = "sell"

    base_duration = 5
    vol_factor = 0.1 / std20 if std20 != 0 else 1
    mom_factor = 1 / (1 + abs(momentum))
    ac_factor = 1 + ac

    duration = base_duration * vol_factor * mom_factor * ac_factor
    duration = max(1, min(10, int(duration)))

    return signal, duration

# ================= TELEGRAM FUNCTION =================
def send_to_telegram(signal, duration, price):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram config manquante")
        return

    message = (
        f"EUR/USD SIGNAL\n"
        f"Type: {signal.upper()}\n"
        f"Entry price: {price}\n"
        f"Duration: {duration} minutes"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception:
        print("Erreur d'envoi Telegram")

# ================= MAIN LOOP =================
def main():
    print("Bot started")
    while True:
        now = datetime.datetime.now()
        if now.hour >= TRADING_END:
            print("Trading session ended")
            break
        if now.hour < TRADING_START:
            time.sleep(60)
            continue

        price = fetch_eurusd()
        if price:
            prices.append(price)
            if len(prices) > 200:
                prices[:] = prices[-200:]

            signal, duration = calculate_signal(prices)
            if signal:
                send_to_telegram(signal, duration, price)
            print(now.strftime("%H:%M:%S"), price, signal, duration)

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()