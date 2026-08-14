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

# Broad, liquid U.S. universe for research. The scanner no longer requires a
# sub-$5 share price because Robinhood supports eligible fractional shares.
UNIVERSE = [
    "SNDL", "PLUG", "OPEN", "CLOV", "NOK", "BB", "MARA", "RIOT", "DNA",
    "JOBY", "BBAI", "SIRI", "GPRO", "LCID", "SOFI", "F", "INTC", "AMD",
    "PLTR", "HOOD", "RIVN", "IONQ", "RKLB", "HIMS", "NU", "T", "SNAP",
]
PAPER_BUDGET = 20.0

# Single keyless market-data implementation: Yahoo public chart endpoint.
BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Trading-Lab/2.0)",
    "Accept": "application/json",
}


def fetch_history(symbol, attempts=2):
    params = {"range": "6mo", "interval": "1d", "events": "history", "includeAdjustedClose": "true"}
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(f"{BASE_URL}/{symbol}", params=params, headers=HEADERS, timeout=20)
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
                if close is not None:
                    rows.append({"Date": pd.to_datetime(ts, unit="s", utc=True), "Close": float(close), "Volume": float(volume or 0)})
            df = pd.DataFrame(rows)
            if df.empty or len(df) < 50:
                raise RuntimeError(f"only {len(df)} usable daily bars returned")
            return df.dropna(subset=["Close"]).set_index("Date").sort_index()
        except Exception as exc:
            last_error = str(exc)
            print(f"{symbol}: market-data attempt {attempt + 1}/{attempts} failed: {exc}")
            if attempt + 1 < attempts:
                time.sleep(2)
    return None


def load_data(symbols):
    data, errors = {}, {}
    for symbol in symbols:
        df = fetch_history(symbol)
        if df is None:
            errors[symbol] = "No usable 6-month history from keyless chart feed"
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
    ret5 = float(close.iloc[-1] / close.iloc[-6] - 1)
    ret20 = float(close.iloc[-1] / close.iloc[-21] - 1)
    ret60 = float(close.iloc[-1] / close.iloc[-61] - 1)
    volatility = float(close.pct_change().tail(20).std() * np.sqrt(252))
    volume_ratio = last_vol / avg_vol if avg_vol else 0.0

    # 100-point research score: momentum/trend/volume, with volatility risk
    # deducted. This is a screening score, not a prediction.
    score = 50.0
    score += 12 if price > sma20 else -12
    score += 12 if sma20 > sma50 else -12
    score += 10 if ret20 > 0 else -10
    score += 8 if ret60 > 0 else -8
    score += 6 if volume_ratio >= 1.0 else -3
    score += 5 if ret5 > 0 else -3
    score -= min(20, max(0, volatility * 100 - 50) * 0.12)
    score = max(0.0, min(100.0, score))

    risk = min(10.0, max(1.0, 3.0 + volatility * 5.0))
    # $20 hypothetical position; no real order is submitted.
    shares = PAPER_BUDGET / price if price > 0 else 0

    return {
        "symbol": symbol,
        "price": round(price, 4),
        "hypothetical_dollars": PAPER_BUDGET,
        "hypothetical_shares": round(shares, 6),
        "score": round(score, 1),
        "risk_score": round(risk, 1),
        "signal": "PAPER BUY" if score >= 70 else "WATCH" if score >= 50 else "AVOID",
        "return_5d_pct": round(ret5 * 100, 2),
        "return_20d_pct": round(ret20 * 100, 2),
        "return_60d_pct": round(ret60 * 100, 2),
        "volatility_pct": round(volatility * 100, 2),
        "volume_vs_20d": round(volume_ratio, 2),
        "trend": "BULLISH" if price > sma20 > sma50 else "MIXED" if price > sma20 or sma20 > sma50 else "BEARISH",
        "robinhood_fractional_status": "VERIFY IN ROBINHOOD APP",
        "history_start": df.index[0].date().isoformat(),
        "history_end": df.index[-1].date().isoformat(),
        "bars": len(df),
    }


def build_agent(name, ranked):
    if name == "Momentum":
        chosen = max(ranked, key=lambda x: (x["return_20d_pct"], x["score"]))
    elif name == "Trend + Volume":
        chosen = max(ranked, key=lambda x: (x["volume_vs_20d"], x["score"]))
    elif name == "Risk-aware":
        chosen = max(ranked, key=lambda x: (x["score"] - x["risk_score"] * 4))
    else:
        chosen = max(ranked, key=lambda x: (x["score"], -x["risk_score"]))

    analyst_a = chosen["score"] >= 60
    analyst_b = chosen["risk_score"] <= 8 and chosen["volume_vs_20d"] >= 0.7
    decision = "PAPER BUY" if analyst_a and analyst_b and chosen["signal"] == "PAPER BUY" else "WATCH / NO TRADE"
    return {
        "agent": name,
        "virtual_cash": PAPER_BUDGET,
        "decision": decision,
        "selection": chosen,
        "analysts": {
            "Analyst A": "PASS" if analyst_a else "REVIEW",
            "Analyst B": "PASS" if analyst_b else "REVIEW",
        },
        "discussion": [
            f"Lead: screened {len(ranked)} current candidates using {name} rules.",
            f"Analyst A: {'supports' if analyst_a else 'challenges'} the candidate on score/trend evidence.",
            f"Analyst B: {'supports' if analyst_b else 'challenges'} the candidate on risk/liquidity evidence.",
            f"Lead: {decision}. This is a simulated $20 paper position only; no live order is submitted.",
        ],
    }


def main():
    data, errors = load_data(UNIVERSE)
    market = [analyze(symbol, df) for symbol, df in data.items()]
    if not market:
        raise RuntimeError("No usable market data returned by the keyless chart feed")

    # Keep the strongest 15 research candidates; do not filter by share price.
    candidates = sorted(market, key=lambda x: (x["score"], -x["risk_score"]), reverse=True)[:15]
    styles = ["Momentum", "Trend + Volume", "Balanced", "Risk-aware"]
    agents = [build_agent(style, candidates) for style in styles]

    # Aggregate votes so the dashboard has a clear consensus state.
    votes = {}
    for agent in agents:
        symbol = agent["selection"]["symbol"]
        votes[symbol] = votes.get(symbol, 0) + (1 if agent["decision"] == "PAPER BUY" else 0)
    consensus = sorted(candidates, key=lambda x: (votes.get(x["symbol"], 0), x["score"]), reverse=True)

    now = datetime.now(timezone.utc).isoformat()
    latest_end = max(row["history_end"] for row in market)
    report = {
        "generated_at": now,
        "mode": "PAPER_ONLY",
        "paper_budget": PAPER_BUDGET,
        "data_source": "Direct Yahoo Finance chart endpoint (keyless HTTP)",
        "latest_market_date": latest_end,
        "universe": UNIVERSE,
        "market": market,
        "candidates": candidates,
        "consensus": [
            {"symbol": row["symbol"], "votes": votes.get(row["symbol"], 0), "score": row["score"], "risk_score": row["risk_score"]}
            for row in consensus[:10]
        ],
        "agents": agents,
        "data_errors": errors,
        "robinhood_note": "Fractional-share availability is not asserted by this keyless feed; verify the ticker in Robinhood before any hypothetical execution.",
    }
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=2))
    (REPORTS / "status.json").write_text(json.dumps({
        "generated_at": now,
        "symbols": len(market),
        "candidates": len(candidates),
        "agents": len(agents),
        "paper_budget": PAPER_BUDGET,
        "failed_symbols": len(errors),
        "latest_market_date": latest_end,
        "data_source": "Direct Yahoo Finance chart endpoint (keyless HTTP)",
        "status": "OK",
    }, indent=2))
    print(f"Generated {len(market)} market records and {len(candidates)} candidates for 4 paper agents")
    print(f"Consensus: {[(x['symbol'], x['votes']) for x in report['consensus'][:5]]}")
    print(f"Latest market date: {latest_end}; skipped: {len(errors)}")


if __name__ == "__main__":
    main()
