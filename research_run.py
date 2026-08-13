import json
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import yfinance as yf

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# Keyless, liquid-ish low-priced/watchlist universe. Failed symbols are skipped.
UNIVERSE = ["SNDL", "PLUG", "OPEN", "CLOV", "NOK", "BB", "MARA", "RIOT", "DNA", "JOBY", "BBAI", "SIRI", "GPRO", "LCID", "WKHS"]
STARTING_CASH = 25.0


def download(symbol, attempts=4):
    last_error = None
    for attempt in range(attempts):
        try:
            # Explicitly request one symbol and normalize both possible yfinance column layouts.
            df = yf.download(symbol, period="6mo", interval="1d", auto_adjust=True,
                             progress=False, threads=False, timeout=20)
            if df is not None and not df.empty:
                if hasattr(df.columns, "levels"):
                    df.columns = df.columns.get_level_values(0)
                required = {"Close", "Volume"}
                if required.issubset(set(df.columns)):
                    df = df.dropna(subset=["Close"])
                    if len(df) >= 50:
                        return df
                last_error = "empty or insufficient data"
            else:
                last_error = "empty response"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2 + attempt * 2)
    return None


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
    return {
        "symbol": symbol,
        "price": round(price, 4),
        "score": round(score, 1),
        "signal": signal,
        "return_20d_pct": round(ret20 * 100, 2),
        "volatility_pct": round(volatility * 100, 2),
        "volume_vs_20d": round(last_vol / avg_vol, 2) if avg_vol else 0,
    }


def main():
    market = []
    errors = {}
    for symbol in UNIVERSE:
        df = download(symbol)
        row = analyze(symbol, df)
        if row:
            market.append(row)
        else:
            errors[symbol] = "No usable 6-month daily data returned by yfinance"

    market.sort(key=lambda x: x["score"], reverse=True)
    if not market:
        raise RuntimeError("No market data was returned by yfinance; refusing to publish an empty report")

    styles = ["Momentum", "Trend + Volume", "Balanced", "Risk-aware"]
    agents = []
    for i, style in enumerate(styles, 1):
        ranked = market[:8]
        if style == "Risk-aware":
            ranked = sorted(market, key=lambda x: (x["volatility_pct"], -x["score"]))[:8]
        elif style == "Momentum":
            ranked = sorted(ranked, key=lambda x: (x["return_20d_pct"], x["score"]), reverse=True)
        elif style == "Trend + Volume":
            ranked = sorted(ranked, key=lambda x: (x["volume_vs_20d"], x["score"]), reverse=True)
        chosen = ranked[0] if ranked else None
        if chosen:
            analyst_a = chosen["score"] >= 55 and chosen["volatility_pct"] < 150
            analyst_b = chosen["volume_vs_20d"] >= 0.8 and chosen["return_20d_pct"] > -10
            decision = "PAPER BUY" if analyst_a and analyst_b and chosen["signal"] == "BUY (PAPER)" else "WATCH / NO TRADE"
        else:
            analyst_a = analyst_b = False
            decision = "NO DATA"
        agents.append({
            "agent": i,
            "strategy": style,
            "virtual_cash": STARTING_CASH,
            "decision": decision,
            "selection": chosen,
            "analysts": {"Analyst A": "PASS" if analyst_a else "REVIEW", "Analyst B": "PASS" if analyst_b else "REVIEW"},
            "discussion": [
                f"Lead: I ranked {len(market)} symbols using {style} rules.",
                f"Analyst A: {'support' if analyst_a else 'do not support'} the candidate based on score and volatility.",
                f"Analyst B: {'support' if analyst_b else 'do not support'} the candidate based on volume and recent return.",
                f"Lead: Final status is {decision}. No live order is submitted.",
            ],
        })

    now = datetime.now(timezone.utc).isoformat()
    report = {
        "generated_at": now,
        "mode": "PAPER_ONLY",
        "data_source": "Yahoo Finance via yfinance",
        "universe": UNIVERSE,
        "market": market,
        "agents": agents,
        "data_errors": errors,
    }
    (REPORTS / "latest.json").write_text(json.dumps(report, indent=2))
    (REPORTS / "status.json").write_text(json.dumps({
        "generated_at": now,
        "symbols": len(market),
        "agents": 4,
        "failed_symbols": len(errors),
        "status": "OK",
    }, indent=2))
    print(f"Generated {len(market)} market records for 4 paper agents; skipped {len(errors)} symbols")


if __name__ == "__main__":
    main()
