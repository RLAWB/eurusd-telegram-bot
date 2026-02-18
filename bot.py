
import os
import requests
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def fetch_candles():
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "EURUSDT",
        "interval": "1m",
        "limit": 50
    }

    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    closes = [float(candle[4]) for candle in data]
    return closes

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)

def calculate_sma(prices, period):
    return sum(prices[-period:]) / period

def main():
    print("Bot started")

    last_signal = None

    for i in range(300):  # 5 hours (1 min checks)
        prices = fetch_candles()

        sma10 = calculate_sma(prices, 10)
        sma20 = calculate_sma(prices, 20)

        print(f"Run {i+1} | SMA10: {sma10} | SMA20: {sma20}")

        if sma10 > sma20 and last_signal != "BUY":
            send_to_telegram("📈 BUY signal (SMA10 crossed above SMA20)")
            last_signal = "BUY"

        elif sma10 < sma20 and last_signal != "SELL":
            send_to_telegram("📉 SELL signal (SMA10 crossed below SMA20)")
            last_signal = "SELL"

        time.sleep(60)

    print("Session ended")

if __name__ == "__main__":
    main()
