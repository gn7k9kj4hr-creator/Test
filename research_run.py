import json
import io
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

UNIVERSE = ["SNDL", "PLUG", "OPEN", "CLOV", "NOK", "BB", "MARA", "RIOT", "DNA", "JOBY", "BBAI", "SIRI", "GPRO", "LCID", "WKHS"]
STARTING_CASH = 25.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nasdaq.com/",
}


def normalize(df):
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if not {"Close", "Volume"}.issubset(df.columns):
        return None
    df = df[["Close", "Volume"]].copy()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
    df = df.dropna(subset=["Close"])
    return df if len(df) >= 50 else None


def yahoo_batch(symbols, attempts=2):
    for attempt in range(attempts):
        try:
            data = yf.download(tickers=symbols, period="6mo", interval="1d", auto_adjust=True,
                               progress=False, threads=True, group_by="ticker", timeout=20)
            if data is None or data.empty:
                raise RuntimeError("empty Yahoo response")
            result = {}
            if isinstance(data.columns, pd.MultiIndex):
                for symbol in symbols:
                    try:
                        if symbol in data.columns.get_level_values(0):
                            df = data[symbol].copy()
                        elif symbol in data.columns.get_level_values(1):
                            df = data.xs(symbol, axis=1, level=1).copy()
                        else:
                            continue
                        df = normalize(df)
                        if df is not None:
                            result[symbol] = df
                    except Exception:
                        continue
            elif len(symbols) == 1:
                df = normalize(data)
                if df is not None:
                    result[symbols[0]] = df
            return result
        except Exception as exc:
            print(f"Yahoo attempt {attempt + 1}/{attempts} failed: {exc}")
            if attempt + 1 < attempts:
                time.sleep(2)
    return {}


def stooq_fallback(symbol, attempts=2):
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    for attempt in range(attempts):
        try:
            r = requests.get(url, timeout=20, headers=HEADERS)
            r.raise_for_status()
            if not r.text.strip() or "No data" in r.text:
                raise RuntimeError("no Stooq data")
            df = pd.read_csv(io.StringIO(r.text))
            if "Date" not in df or "Close" not in df or "Volume" not in df:
                raise RuntimeError("unexpected Stooq response")
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = normalize(df.set_index("Date"))
            if df is not None:
                return df
        except Exception as exc:
            print(f"Stooq {symbol} attempt {attempt + 1}/{attempts} failed: {exc}")
            if attempt + 1 < attempts:
                time.sleep(2)
    return None


def nasdaq_fallback(symbol, attempts=2):
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=210)
    url = f"https://api.nasdaq.com/api/quote/{symbol}/historical?assetclass=stocks&fromdate={start.isoformat()}&limit=500&todate={end.isoformat()}"
    for attempt in range(attempts):
        try:
            r = requests.get(url, timeout=20, headers=HEADERS)
            r.raise_for_status()
            payload = r.json()
            rows = ((payload.get("data") or {}).get("tradesTable") or {}).get("rows") or []
            if not rows:
                raise RuntimeError("empty Nasdaq historical response")
            records = []
            for row in rows:
                date = pd.to_datetime(row.get("date"), errors="coerce")
                close = pd.to_numeric(str(row.get("close", "")).replace("$", "").replace(",", ""), errors="coerce")
                volume = pd.to_numeric(str(row.get("volume", "")).replace(",", ""), errors="coerce")
                if pd.notna(date) and pd.notna(close):
                    records.append({"Date": date, "Close": close, "Volume": volume if pd.notna(volume) else 0})
            if not records:
                raise RuntimeError("Nasdaq returned no parseable rows")
            df = normalize(pd.DataFrame(records).set_index("Date").sort_index())
            if df is not None:
                return df
            raise RuntimeError("Nasdaq returned fewer than 50 usable rows")
        except Exception as exc:
            print(f"Nasdaq {symbol} attempt {attempt + 1}/{attempts} failed: {exc}")
            if attempt + 1 < attempts:
                time.sleep(2)
    return None


def load_data(symbols):
    data = yahoo_batch(symbols, attempts=2)
    errors = {}
    for symbol in symbols:
        if symbol in data:
            continue
        print(f"{symbol}: Yahoo unavailable; trying Stooq")
        df = stooq_fallback(symbol, attempts=2)
        if df is None:
            print(f"{symbol}: Stooq unavailable; trying Nasdaq")
            df = nasdaq_fallback(symbol, attempts=2)
        if df is not None:
            data[symbol] = df
        else:
            errors[symbol] = "No usable historical data from Yahoo, Stooq, or Nasdaq"
    return data, errors


def analyze(symbol, df):
    if df is None or len(df) < 50:
        return None
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)
    price = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    avg_vol = float(volume.tail(20).mean())
    last_vol = float(volume.iloc[-1])
    ret20 = float(close.iloc[-1] / close.iloc[-21] - 1)
    volatility = float(close.pct_change().tail(20).std() * np.sqrt(252))
    score = 50 + (10 if price > sma20 else -10) + (10 if sma20 > sma50 else -10) + (10 if ret20 > 0 else -10) + (5 if last_vol > avg_vol else 0)
    signal = "BUY (PAPER)" if score >= 65 else "WATCH" if score >= 45 else "AVOID"
    return {"symbol": symbol, "price": round(price, 4), "score": round(score, 1), "signal": signal,
            "return_20d_pct": round(ret20 * 100, 2), "volatility_pct": round(volatility * 100, 2),
            "volume_vs_20d": round(last_vol / avg_vol, 2) if avg_vol else 0}


def main():
    data, errors = load_data(UNIVERSE)
    market = [row for symbol, df in data.items() if (row := analyze(symbol, df)) is not None]
    penny_candidates = [row for row in market if 0 < row["price"] < 5]
    market.sort(key=lambda x: x["score"], reverse=True)
    penny_candidates.sort(key=lambda x: x["score"], reverse=True)
    if not market:
        raise RuntimeError("No usable market data from Yahoo, Stooq, or Nasdaq")
    if not penny_candidates:
        raise RuntimeError("Market data arrived, but no current sub-$5 candidates were found")

    styles = ["Momentum", "Trend + Volume", "Balanced", "Risk-aware"]
    agents = []
    for i, style in enumerate(styles, 1):
        ranked = penny_candidates[:8]
        if style == "Risk-aware":
            ranked = sorted(penny_candidates, key=lambda x: (x["volatility_pct"], -x["score"]))[:8]
        elif style == "Momentum":
            ranked = sorted(ranked, key=lambda x: (x["return_20d_pct"], x["score"]), reverse=True)
        elif style == "Trend + Volume":
            ranked = sorted(ranked, key=lambda x: (x["volume_vs_20d"], x["score"]), reverse=True)
        chosen = ranked[0]
        analyst_a = chosen["score"] >= 55 and chosen["volatility_pct"] < 150
        analyst_b = chosen["volume_vs_20d"] >= 0.8 and chosen["return_20d_pct"] > -10
        decision = "PAPER BUY" if analyst_a and analyst_b and chosen["signal"] == "BUY (PAPER)" else "WATCH / NO TRADE"
        agents.append({"agent": i, "strategy": style, "virtual_cash": STARTING_CASH, "decision": decision,
            "selection": chosen,
            "analysts": {"Analyst A": "PASS" if analyst_a else "REVIEW", "Analyst B": "PASS" if analyst_b else "REVIEW"},
            "discussion": [
                f"Lead: ranked {len(penny_candidates)} current sub-$5 candidates using {style} rules.",
                f"Analyst A: {'support' if analyst_a else 'do not support'} based on score and volatility.",
                f"Analyst B: {'support' if analyst_b else 'do not support'} based on volume and recent return.",
                f"Lead: final status is {decision}. No live order is submitted."
            ]})

    now = datetime.now(timezone.utc).isoformat()
    report = {"generated_at": now, "mode": "PAPER_ONLY",
              "data_source": "Yahoo Finance via yfinance; Stooq; Nasdaq historical fallback",
              "universe": UNIVERSE, "eligible_under_5": len(penny_candidates),
              "market": market, "agents": agents, "data_errors": errors}
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=2))
    (REPORTS / "status.json").write_text(json.dumps({"generated_at": now, "symbols": len(market),
        "eligible_under_5": len(penny_candidates), "agents": 4, "failed_symbols": len(errors), "status": "OK"}, indent=2))
    print(f"Generated {len(market)} market records, {len(penny_candidates)} under $5, for 4 paper agents; skipped {len(errors)} symbols")


if __name__ == "__main__":
    main()
