# AI Trading Lab — Mobile/PWA v5

A **paper-trading / research-only** dashboard. It contains **no live order execution**.

## What changed
- Mobile-first PWA that works in Safari/Chrome and can be added to a phone home screen.
- Dashboard can load `reports/latest.json` automatically when hosted, or import a JSON report manually.
- Better simulator accounting: daily/weekly loss stops, hard drawdown stop, mark-to-market equity, and safer data validation.
- GitHub Actions workflow runs the research engine and publishes the static dashboard to GitHub Pages.
- No API keys or broker credentials are required.

## Run locally
```bash
pip install -r engine/requirements.txt
python -m engine.worker
python -m http.server 8000 -d app
```
Then open `http://localhost:8000`.

## GitHub Pages
1. Create a GitHub repository and upload this folder's contents.
2. In **Settings → Pages**, choose **GitHub Actions** as the source.
3. The included workflow runs the simulator and deploys the `app/` folder.
4. The dashboard will read `app/reports/latest.json` after the workflow copies the generated report there.

> This is a research tool, not financial advice. Backtests can be misleading and do not predict future performance.
