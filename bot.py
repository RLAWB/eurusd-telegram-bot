import os
import requests
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def fetch_candles():
    try:
        url = "https://fapi.binance.com/fapi/v1/indexPriceKlines"
        params = {
            "pair": "EURUSD",
            "interval": "1m",
            "limit": 50
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if not isinstance(data, list):
            print("API Error:", data)
            return None

        closes = [float(candle[4]) for candle in data]
        return closes

    except Exception as e:
        print("Fetch error:", e)
        return None


def send_to_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


def calculate_sma(prices, period):
    return sum(prices[-period:]) / period


def main():
    print("Bot started")

    last_signal = None

    for i in range(10):  # Short test first
        prices = fetch_candles()

        if prices is None:
            time.sleep(60)
            continue

        sma10 = calculate_sma(prices, 10)
        sma20 = calculate_sma(prices, 20)

        print(f"Run {i+1} | SMA10: {sma10} | SMA20: {sma20}")

        if sma10 > sma20 and last_signal != "BUY":
            send_to_telegram("BUY signal")
            last_signal = "BUY"

        elif sma10 < sma20 and last_signal != "SELL":
            send_to_telegram("SELL signal")
            last_signal = "SELL"

        time.sleep(60)

    print("Session ended")


if __name__ == "__main__":
    main()
