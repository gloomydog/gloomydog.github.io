"""Incrementally update daily prices in data/<NAME>.csv.

- First run: downloads everything from START.
- Later runs: downloads only dates after the last stored date and appends them.
- Today's bar is skipped until the US market has closed (avoids saving a partial bar).

pip install yfinance pandas
"""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

DATA = Path(__file__).resolve().parent.parent / "naaim-data"
START = "2006-07-01"  # NAAIM starts 2006-07
SYMBOLS = {"GSPC": "^GSPC", "IXIC": "^IXIC", "QQQ": "QQQ", "DJI": "^DJI"}
COLS = ["date", "open", "high", "low", "close"]


def last_complete_day() -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.hour * 60 + now.minute < 16 * 60 + 30:  # before 16:30 ET -> today not final
        now -= timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def update(name: str, ticker: str, cutoff: str) -> None:
    path = DATA / f"{name}.csv"
    old = pd.read_csv(path, dtype={"date": str}) if path.exists() else pd.DataFrame(columns=COLS)
    last = old["date"].max() if len(old) else None
    start = (pd.Timestamp(last) + pd.Timedelta(days=1)).strftime("%Y-%m-%d") if last else START
    if start > cutoff:
        print(f"{name}: up to date ({last})")
        return

    df = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    if df.empty:
        print(f"{name}: no new rows")
        return
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].dropna().reset_index()
    df.columns = COLS
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df[(df["date"] >= start) & (df["date"] <= cutoff)].round(2)
    if df.empty:
        print(f"{name}: no new rows")
        return

    out = pd.concat([old, df], ignore_index=True).drop_duplicates("date", keep="first")
    out.to_csv(path, index=False)
    print(f"{name}: +{len(df)} rows ({df['date'].min()} .. {df['date'].max()})")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    cutoff = last_complete_day()
    for name, ticker in SYMBOLS.items():
        update(name, ticker, cutoff)
