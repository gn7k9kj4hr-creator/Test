import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

UNIVERSE = ["SNDL", "PLUG", "OPEN", "CLOV", "NOK", "BB", "MARA", "RIOT", "DNA", "JOBY", "BBAI", "SIRI", "GPRO", "LCID", "WKHS"]
STARTING_CASH = 25.0

# One keyless HTTP market-data implementation. This uses Yahoo's public chart
# endpoint directly instead of yfinance/Stooq/Nasdaq wrappers. A ticker gets
# one request plus one retry; a bad ticker never aborts the whole run.
BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Trading-Lab/1.0)",
    "Accept": "application/json",
}


def fetch_history(symbol, attempts=2):
    url = f"{BASE_URL}/{symbol}"
    params = {"range": "6mo", "interval": "1d", "events": "history", "includeAdjustedClose": "true"}
    last_error = None

    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            payload = response.json()
            result = (payload.get("chart") or {}).get("result")
            if not result:
                raise RuntimeError("empty chart result")

            item = result[0]
            timestamps = item.get("timestamp") or []
            quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
            closes = quote.get("close") or []
            volumes = quote.get("volume") or []

            rows = []
            for ts, close, volume in zip(timestamps, closes, volumes):
                if close is None:
                    continue
                rows.append({
                    "Date": pd.to_datetime(ts, unit="s", utc=True),
                    "Close": float(close),
                    "Volume": float(volume or 0),
                })

            df = pd.DataFrame(rows)
            if df.empty:
                raise RuntimeError("no usable daily bars")
            df = df.dropna(subset=["Close"]).set_index("Date").sort_index()
            if len(df) < 50:
                raise RuntimeError(f"only {len(df)} daily bars returned")
            return df
        except Exception as exc:
            last_error = str(exc)
            print(f"{symbol}: market-data attempt {attempt + 1}/{attempts} failed: {exc}")
            if attempt + 1 < attempts:
                time.sleep(2)

    return None


def load_data(symbols):
    data = {}
    errors = {}
    for symbol in symbols:
        df = fetch_history(symbol, attempts=2)
        if df is None:
            errors[symbol] = "No usable 6-month daily history from keyless chart feed"
        else:
            data[symbol] = df
    return data, errors


def analyze(symbol, df):
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
    return {
        "symbol": symbol,
        "price": round(price, 4),
        "score": round(score, 1),
        "signal": signal,
        "return_20d_pct": round(ret20 * 100, 2),
        "volatility_pct": round(volatility * 100, 2),
        "volume_vs_20d": round(last_vol / avg_vol, 2) if avg_vol else 0,
        "history_start": df.index[0].date().isoformat(),
        "history_end": df.index[-1].date().isoformat(),
        "bars": len(df),
    }


def main():
    data, errors = load_data(UNIVERSE)
    market = [row for symbol, df in data.items() if (row := analyze(symbol, df)) is not None]
    penny_candidates = [row for row in market if 0 < row["price"] < 5]
    market.sort(key=lambda x: x["score"], reverse=True)
    penny_candidates.sort(key=lambda x: x["score"], reverse=True)

    if not market:
        raise RuntimeError("No usable market data returned by the keyless chart feed")
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
        agents.append({
            "agent": i,
            "strategy": style,
            "virtual_cash": STARTING_CASH,
            "decision": decision,
            "selection": chosen,
            "analysts": {
                "Analyst A": "PASS" if analyst_a else "REVIEW",
                "Analyst B": "PASS" if analyst_b else "REVIEW",
            },
            "discussion": [
                f"Lead: ranked {len(penny_candidates)} current sub-$5 candidates using {style} rules.",
                f"Analyst A: {'support' if analyst_a else 'do not support'} based on score and volatility.",
                f"Analyst B: {'support' if analyst_b else 'do not support'} based on volume and recent return.",
                f"Lead: final status is {decision}. No live order is submitted.",
            ],
        })

    now = datetime.now(timezone.utc).isoformat()
    latest_end = max(row["history_end"] for row in market)
    report = {
        "generated_at": now,
        "mode": "PAPER_ONLY",
        "data_source": "Direct Yahoo Finance chart endpoint (keyless HTTP)",
        "latest_market_date": latest_end,
        "universe": UNIVERSE,
        "eligible_under_5": len(penny_candidates),
        "market": market,
        "agents": agents,
        "data_errors": errors,
    }
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=2))
    (REPORTS / "status.json").write_text(json.dumps({
        "generated_at": now,
        "symbols": len(market),
        "eligible_under_5": len(penny_candidates),
        "agents": 4,
        "failed_symbols": len(errors),
        "latest_market_date": latest_end,
        "data_source": "Direct Yahoo Finance chart endpoint (keyless HTTP)",
        "status": "OK",
    }, indent=2))
    print(f"Generated {len(market)} market records, {len(penny_candidates)} under $5, for 4 paper agents")
    print(f"Latest market date: {latest_end}; skipped: {len(errors)}")


if __name__ == "__main__":
    main()
