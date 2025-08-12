import os
import time
import requests
from datetime import datetime
import pytz
import yfinance as yf
import pandas as pd
import numpy as np

# Environment variables from Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Error sending message:", e)

def is_market_hours():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    return now.weekday() < 5 and (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30))

def fetch_nifty_data():
    nifty = yf.Ticker("^NSEI")
    data = nifty.history(period="1d", interval="5m")
    return data

def calculate_indicators(df):
    # VWAP
    df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()

    # MACD
    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA12"] - df["EMA26"]
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Supertrend
    period = 10
    multiplier = 3
    hl2 = (df["High"] + df["Low"]) / 2
    atr = df["High"].rolling(period).max() - df["Low"].rolling(period).min()
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)
    df["Supertrend"] = np.where(df["Close"] > upperband, 1, np.where(df["Close"] < lowerband, -1, 0))

    return df

def generate_signal(df):
    latest = df.iloc[-1]
    signal = []

    # MACD Signal
    if latest["MACD"] > latest["Signal"]:
        signal.append("MACD: Bullish")
    else:
        signal.append("MACD: Bearish")

    # VWAP Signal
    if latest["Close"] > latest["VWAP"]:
        signal.append("Above VWAP")
    else:
        signal.append("Below VWAP")

    # Supertrend Signal
    if latest["Supertrend"] == 1:
        signal.append("Supertrend: Buy")
    elif latest["Supertrend"] == -1:
        signal.append("Supertrend: Sell")

    return " | ".join(signal)

def main():
    last_message = None
    while True:
        if is_market_hours():
            df = fetch_nifty_data()
            df = calculate_indicators(df)
            message = f"NIFTY {df['Close'].iloc[-1]} → {generate_signal(df)}"
            if message != last_message:
                send_telegram_message(message)
                last_message = message
            time.sleep(300)  # Every 5 min
        else:
            print("Outside market hours...")
            time.sleep(600)

if __name__ == "__main__":
    main()
