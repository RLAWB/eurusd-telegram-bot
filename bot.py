import os
import requests
import time
import pandas as pd
import numpy as np

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def fetch_candles_df(pair="EURUSD", interval="1m", limit=100):
    """
    Fetch recent klines from Binance indexPriceKlines and return a DataFrame
    with columns: ['open_time','open','high','low','close'] (floats where appropriate).
    """
    try:
        url = "https://fapi.binance.com/fapi/v1/indexPriceKlines"
        params = {"pair": pair, "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if not isinstance(data, list):
            print("API Error:", data)
            return None

        # Binance kline format: [open_time, open, high, low, close, ...]
        rows = []
        for candle in data:
            rows.append({
                "open_time": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
            })

        df = pd.DataFrame(rows)
        # Use open_time as index (optional)
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df.set_index('open_time', inplace=True)
        return df

    except Exception as e:
        print("Fetch error:", e)
        return None


def send_to_telegram(message):
    try:
        if not TELEGRAM_TOKEN or not CHAT_ID:
            print("Telegram credentials not set; message:", message)
            return
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)


def supertrend_signals(df, period=10, multiplier=3.0, atr_method='wilder'):
    """
    Compute SuperTrend and generate signals.
    Returns DataFrame with added columns: tr, atr, upperband, lowerband, supertrend, trend, signal, position.
    signal:  1 (buy) when trend flips to up
            -1 (sell) when trend flips to down
             0 (no action)
    position: 1 if in long, 0 if flat
    """
    df = df.copy()
    # Validate columns
    for col in ['high', 'low', 'close']:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    if atr_method == 'wilder':
        df['atr'] = df['tr'].rolling(window=period, min_periods=period).mean()
        first_valid = df['atr'].first_valid_index()
        if first_valid is not None:
            atr_vals = df['atr'].to_numpy()
            tr_vals = df['tr'].to_numpy()
            idx = df.index.get_loc(first_valid)
            for i in range(idx + 1, len(df)):
                atr_vals[i] = (atr_vals[i-1] * (period - 1) + tr_vals[i]) / period
            df['atr'] = atr_vals
    else:
        df['atr'] = df['tr'].rolling(window=period, min_periods=1).mean()

    hl2 = (df['high'] + df['low']) / 2.0
    df['upperband'] = hl2 + multiplier * df['atr']
    df['lowerband'] = hl2 - multiplier * df['atr']

    df['supertrend'] = np.nan
    df['trend'] = True

    start = df['atr'].first_valid_index()
    if start is None:
        df['signal'] = 0
        df['position'] = 0
        return df

    start_pos = df.index.get_loc(start)
    df.iat[start_pos, df.columns.get_loc('supertrend')] = df.iloc[start_pos]['lowerband']
    df.iat[start_pos, df.columns.get_loc('trend')] = True

    for i in range(start_pos + 1, len(df)):
        prev_trend = bool(df.iloc[i-1]['trend'])
        prev_upper = df.iloc[i-1]['upperband']
        prev_lower = df.iloc[i-1]['lowerband']

        curr_upper = df.iloc[i]['upperband']
        curr_lower = df.iloc[i]['lowerband']
        close = df.iloc[i]['close']

        if prev_trend:
            curr_upper = min(curr_upper, prev_upper)
        else:
            curr_lower = max(curr_lower, prev_lower)

        if close > prev_upper:
            curr_trend = True
        elif close < prev_lower:
            curr_trend = False
        else:
            curr_trend = prev_trend

        df.iat[i, df.columns.get_loc('upperband')] = curr_upper
        df.iat[i, df.columns.get_loc('lowerband')] = curr_lower
        df.iat[i, df.columns.get_loc('trend')] = curr_trend
        df.iat[i, df.columns.get_loc('supertrend')] = curr_lower if curr_trend else curr_upper

    # Signals: detect trend flips
    df['trend_prev'] = df['trend'].shift(1)
    df['signal'] = 0
    df.loc[(df['trend_prev'] == False) & (df['trend'] == True), 'signal'] = 1
    df.loc[(df['trend_prev'] == True) & (df['trend'] == False), 'signal'] = -1

    # Position: simple long-only stateful position
    df['position'] = 0
    pos = 0
    for i in range(len(df)):
        sig = int(df['signal'].iat[i])
        if sig == 1:
            pos = 1
        elif sig == -1:
            pos = 0
        df.iat[i, df.columns.get_loc('position')] = pos

    df.drop(columns=['trend_prev'], inplace=True)
    return df


def main():
    print("Bot started (SuperTrend signals)")

    # Short alive test messages
    for _ in range(3):
        send_to_telegram("✅ Bot is alive and running (SuperTrend)")
        time.sleep(10)

    last_signal = None  # track last sent signal to avoid duplicates

    # Main loop (example: 10 iterations for testing; change to while True for production)
    for run in range(10):
        df = fetch_candles_df(limit=100)
        if df is None or df.empty:
            print("No data, retrying in 60s")
            time.sleep(60)
            continue

        try:
            out = supertrend_signals(df, period=10, multiplier=3.0, atr_method='wilder')
        except Exception as e:
            print("Indicator error:", e)
            time.sleep(60)
            continue

        latest_signal = int(out['signal'].iloc[-1]) if not out['signal'].isna().all() else 0
        latest_close = out['close'].iloc[-1]
        latest_trend = out['trend'].iloc[-1]
        latest_super = out['supertrend'].iloc[-1]

        print(f"Run {run+1} | Close: {latest_close} | Signal: {latest_signal} | Trend(up?): {latest_trend}")

        # Only send when signal changes (and not zero)
        if latest_signal == 1 and last_signal != "BUY":
            msg = f"BUY signal (SuperTrend)\nPrice: {latest_close}\nSuperTrend: {latest_super}"
            send_to_telegram(msg)
            last_signal = "BUY"

        elif latest_signal == -1 and last_signal != "SELL":
            msg = f"SELL signal (SuperTrend)\nPrice: {latest_close}\nSuperTrend: {latest_super}"
            send_to_telegram(msg)
            last_signal = "SELL"

        else:
            # No new actionable signal
            pass

        # Wait for next candle; in live use align with candle interval
        time.sleep(60)

    print("Session ended")


if __name__ == "__main__":
    main()
