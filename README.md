# AI Trading Agent

A compact **research and paper-trading** agent rebuilt around the six requested files.

## Pipeline

1. Generate five candidate strategies with an LLM.
2. Download historical market data with yfinance.
3. Backtest each candidate with Backtrader.
4. Require return, Sharpe, win-rate, and trade-count thresholds.
5. Send approved orders only to the **Alpaca paper-trading endpoint**.
6. Print paper-account value, cash, positions, and P&L.

No live-money brokerage endpoint is configured by this project.

## Files

- `requirements.txt` — pinned Python dependencies
- `.env` — placeholder environment variables; replace locally and never put real secrets in Git
- `strategy_generator.py` — LLM strategy generation
- `backtester.py` — historical strategy evaluation
- `paper_trader.py` — Alpaca paper-trading adapter
- `main.py` — end-to-end cycle

## Setup

```bash
mkdir ai-trading-agent
cd ai-trading-agent
pip install -r requirements.txt
```

Set your credentials in a **local** `.env` file, then run:

```bash
python main.py
```

The default example backtests and paper-trades `SPY`, matching the supplied specification. If you adapt it to a different research universe, keep execution on a paper account while testing.

> This project is for software/research experimentation and paper trading. Backtests are hypothetical and do not predict future results.
