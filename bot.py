import os
import time
import json
import websocket-client
import requests
import pandas as pd
import numpy as np

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# TELEGRAM
# =========================
def send_to_telegram(message):
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID:
            print(message)
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)

    except Exception as e:
        print("Telegram error:", e)


# =========================
# 1s CANDLE ENGINE
# =========================
candles = []
current_candle = None
last_trade_time = 0


def process_tick(price, timestamp):
    global current_candle, candles

    sec = timestamp // 1000

    if current_candle is None:
        current_candle = {
            "time": sec,
            "open": price,
            "high": price,
            "low": price,
            "close": price
        }
        return

    if sec == current_candle["time"]:
        current_candle["high"] = max(current_candle["high"], price)
        current_candle["low"] = min(current_candle["low"], price)
        current_candle["close"] = price

    else:
        candles.append(current_candle)

        if len(candles) > 300:
            candles.pop(0)

        current_candle = {
            "time": sec,
            "open": price,
            "high": price,
            "low": price,
            "close": price
        }

        run_strategy()


# =========================
# DATAFRAME
# =========================
def get_df():
    df = pd.DataFrame(candles)

    if df.empty:
        return df

    df["ma"] = df["close"].rolling(30).mean()
    return df


# =========================
# SUPER TREND
# =========================
def supertrend_signals(df, period=10, multiplier=3.0):
    df = df.copy()

    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()

    df["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = df["tr"].rolling(period).mean()

    hl2 = (df["high"] + df["low"]) / 2
    df["upperband"] = hl2 + multiplier * df["atr"]
    df["lowerband"] = hl2 - multiplier * df["atr"]

    df["supertrend"] = np.nan
    df["trend"] = True

    start = df["atr"].first_valid_index()
    if start is None:
        df["signal"] = 0
        return df

    start_pos = df.index.get_loc(start)

    df.iat[start_pos, df.columns.get_loc("supertrend")] = df.iloc[start_pos]["lowerband"]
    df.iat[start_pos, df.columns.get_loc("trend")] = True

    for i in range(start_pos + 1, len(df)):
        prev_trend = df.iloc[i - 1]["trend"]
        prev_upper = df.iloc[i - 1]["upperband"]
        prev_lower = df.iloc[i - 1]["lowerband"]

        curr_upper = df.iloc[i]["upperband"]
        curr_lower = df.iloc[i]["lowerband"]
        close = df.iloc[i]["close"]

        if close > prev_upper:
            trend = True
        elif close < prev_lower:
            trend = False
        else:
            trend = prev_trend

        df.iat[i, df.columns.get_loc("trend")] = trend
        df.iat[i, df.columns.get_loc("supertrend")] = curr_lower if trend else curr_upper

    df["trend_prev"] = df["trend"].shift(1)
    df["signal"] = 0

    df.loc[(df["trend_prev"] == False) & (df["trend"] == True), "signal"] = 1
    df.loc[(df["trend_prev"] == True) & (df["trend"] == False), "signal"] = -1

    return df


# =========================
# STRATEGY
# =========================
def run_strategy():
    global last_trade_time

    df = get_df()

    if len(df) < 50:
        return

    price = df["close"].iloc[-1]
    ma = df["ma"].iloc[-1]

    if pd.isna(ma):
        return

    bullish = price > ma
    bearish = price < ma

    volatility = df["close"].diff().abs().tail(10).mean()
    if volatility < price * 0.00005:
        return

    try:
        out = supertrend_signals(df)
        latest_signal = int(out["signal"].iloc[-2])
        latest_close = out["close"].iloc[-2]
    except:
        return

    if time.time() - last_trade_time < 15:
        return

    if latest_signal == 1 and bullish:
        send_to_telegram(f"🚀 BUY\nPrice: {latest_close}\nMA: {ma}")
        last_trade_time = time.time()

    elif latest_signal == -1 and bearish:
        send_to_telegram(f"🔻 SELL\nPrice: {latest_close}\nMA: {ma}")
        last_trade_time = time.time()


# =========================
# WEBSOCKET
# =========================
def on_message(ws, message):
    data = json.loads(message)
    process_tick(float(data["p"]), data["T"])


def on_error(ws, error):
    print("Error:", error)


def on_close(ws, code, msg):
    print("Disconnected → reconnecting...")
    time.sleep(5)
    raise Exception("Reconnect")


def start():
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws/btcusdt@trade",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()


# =========================
# MAIN (GITHUB ACTIONS SAFE)
# =========================
if __name__ == "__main__":
    print("Bot started (GitHub Actions mode)")

    start_time = time.time()
    MAX_RUNTIME = 3300  # ~55 minutes

    while True:
        try:
            start()
        except Exception as e:
            print("Restarting WS:", e)
            time.sleep(5)

        if time.time() - start_time > MAX_RUNTIME:
            print("Stopping before GitHub timeout")
            break
