# Stock Picker: Long-Term Model

A beginner-friendly, tweakable stock-picking project. It predicts which S&P 500 stocks are likely to beat the typical stock over the next 12 months, then honestly backtests that idea against the S&P 500.

**Educational project, not financial advice.**

## Setup (one time, in Terminal)

```bash
cd ~/Documents/stock-model
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python run.py --demo             # offline test on fake data (results are meaningless)
python run.py                    # real data (first run downloads several minutes, then cached in data/)
python run.py --refresh          # force a fresh download
python run.py --no-fundamentals  # skip the slow P/E lookups for the picks
```

Results print to the terminal and save to `outputs/` (growth chart, yearly returns, current picks).

## Market news

```bash
python news.py          # collect today's headlines and rebuild the news page
python news.py --open   # same, then open the page in your browser
```

Pulls headlines from MarketWatch, WSJ, CNBC, Bloomberg, FT, Seeking Alpha, Investing.com,
Google News, the Federal Reserve, the SEC, and Yahoo headlines for the tickers in `WATCHLIST`.
- `outputs/news.html`: one page with the last few days of headlines, with search and source filters.
- `data/news/headlines.csv`: every headline ever collected. Nothing is deleted, so this becomes the
  news history to test a news feature on later. Feeds only keep a few days, so run it daily.

Change sources, the watchlist and how many days the page shows in `config.py`.

**Runs automatically in the cloud.** GitHub runs `news.py` every morning (11:00 UTC) using
`.github/workflows/news.yml`, saves the new headlines to this repo, and publishes the page at
https://bhrugu1203.github.io/stock-model/. Your Mac doesn't need to be on.
- Run it now: on GitHub, open **Actions → Daily market news → Run workflow**.
- Get the latest headlines onto your Mac before working with them: `git pull`.
- Don't commit a `news.py` run made on your Mac; it would clash with the cloud's copy of `headlines.csv`.
  If you ran it locally, throw that away with `git checkout data/news outputs/news.html` before `git pull`.

## Where to tweak

| File | What it controls |
|---|---|
| `config.py` | stock universe (historical or today's list), dates, horizon, top-fraction, trading costs, model settings |
| `features.py` | the inputs the model sees. Add a function plus one line in `FEATURE_BUILDERS` |
| `backtest.py` | walk-forward training and the scorecard |
| `picks.py` | today's top picks and the fundamentals shown |
| `data.py` | downloading and caching prices and past S&P 500 membership |
| `news.py` | the news collector and news page |

## Ideas to try next
1. Change `TOP_FRACTION` (0.1, 0.3) and `HORIZON_MONTHS` (6, 24, 36).
2. Add features in `features.py` (e.g. 3-month momentum, price vs 200-day average).
3. Swap the model in `backtest.make_model()` (try `GradientBoostingClassifier`).
4. Set `UNIVERSE = "today"` and compare with `"historical"` to see how much survivorship bias inflates results.
5. Add real historical fundamentals (needs paid data or SEC filings). This is where a finance major can add the most value.

## Limitations (read these)
- **Survivorship bias (reduced, not gone):** by default the backtest uses the S&P 500 as it actually was on each date
  (membership history from github.com/fja05680/sp500), so stocks later dropped from the index are included.
  But Yahoo Finance has no prices for many companies that went bust, were bought out or changed ticker.
  The run prints how many real members are covered. The missing ones are mostly not random, so results can still be off.
- **Reused tickers:** if a ticker was later given to a different company, Yahoo returns the new company's prices.
- **Price-only features:** the model is not trained on fundamentals; picks only *display* current ones.
- **Small sample:** about 10 yearly results. One great or terrible year means little.
- **Simplified costs, no taxes.**
- Beating the S&P 500 is hard. "No edge" is a normal, honest result.
- If you tune settings until the backtest looks great, you are fitting to the past. Always keep a final period you never tune on.
