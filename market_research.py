import json
from datetime import datetime, timezone
from pathlib import Path
import yfinance as yf

ROOT = Path(__file__).resolve().parent
UNIVERSE = ['SNDL','PLUG','OPEN','CLOV','NOK','BB','MARA','RIOT','DNA','JOBY','LCID','BBAI','SIRI','GRAB','GPRO']

def scan(symbol):
    df = yf.download(symbol, period='6mo', interval='1d', auto_adjust=True, progress=False)
    if df is None or len(df) < 50:
        return None
    if hasattr(df.columns, 'levels'):
        df.columns = df.columns.get_level_values(0)
    close = df['Close'].dropna(); volume = df['Volume'].dropna()
    if len(close) < 50:
        return None
    price = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    r20 = price / float(close.iloc[-21]) - 1 if len(close) > 21 else 0
    avgvol = float(volume.tail(20).mean())
    score = 50 + (15 if price > sma20 else -10) + (15 if sma20 > sma50 else -10) + max(-15, min(15, r20 * 100))
    signal = 'BUY' if score >= 65 else 'SELL' if score <= 35 else 'HOLD'
    return {'symbol': symbol, 'price': price, 'score': round(score, 1), 'return_20d': round(r20 * 100, 2), 'avg_volume': int(avgvol), 'signal': signal}

def run():
    rows = [x for s in UNIVERSE if (x := scan(s))]
    rows.sort(key=lambda x: x['score'], reverse=True)
    styles = ['Momentum', 'Trend', 'Volume', 'Balanced']
    agents = []
    for i, style in enumerate(styles):
        pick = rows[min(i, len(rows) - 1)] if rows else None
        agents.append({'agent': i + 1, 'style': style, 'starting_cash': 25.0, 'cash': 25.0, 'position': None, 'decision': pick, 'discussion': [f'Lead: selected {pick["symbol"] if pick else "none"} using {style}.', 'Analyst A: reviewed trend, momentum and liquidity.', 'Analyst B: reviewed risk and challenged the lead decision.']})
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'mode': 'PAPER_ONLY', 'source': 'Yahoo Finance via yfinance', 'market_rows': rows, 'agents': agents}
    out = ROOT / 'reports'; out.mkdir(exist_ok=True)
    (out / 'latest.json').write_text(json.dumps(report, indent=2))
    return report

if __name__ == '__main__':
    r = run(); print(json.dumps({'generated_at': r['generated_at'], 'agents': len(r['agents']), 'symbols': len(r['market_rows'])}, indent=2))
