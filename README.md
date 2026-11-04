# Bhrugu's Stock Model

A beginner-friendly, tweakable stock-picking project. It predicts which S&P 500 stocks are likely to beat the typical stock over the next 12 months, then honestly backtests that idea against the S&P 500.

By default the model is a simple score: the average of each stock's rank on six company financials from SEC filings (value, profitability, growth, debt). Price patterns are switched off because they made 2016-2022 results worse; set `USE_PRICE_FEATURES = True` to compare.

The portfolio is the top 20% of stocks by score (about 100), each held in proportion to its company's market value,
like the S&P 500 itself (`WEIGHTING = "size"` in `config.py`; `"equal"` for the same amount in each). Equal weighting
lost badly to the index in 2023-2026 because a few giant companies drove the market; size weighting beat it in both
2016-2022 and 2023-2026. The catch: the biggest handful of holdings make up most of the portfolio.

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
python run.py --final            # also score the held-out years (2023+); do this rarely
```

Results print to the terminal and save to `outputs/` (growth chart, yearly returns, current picks).

## Website: today's picks, track record, news

```bash
python forecast.py --no-record   # picks for 6 months, 1 year and 2 years, each with a walk-forward track record
                                 # (--no-record: leave the official live record to the cloud run)
python dashboard.py     # rebuild the website in outputs/site/index.html
```

Live at https://bhrugu1203.github.io/stock-model/, rebuilt by GitHub every morning (see below). Tabs:
- **Today's picks**: the top stocks for each holding period, with the model's score, conviction, an 80% likely
  range and chance of loss (from the stock's recent volatility), and what stands out in its financials.
- **Backtest**: what would have happened if you had bought the picks every quarter since 2016 and held them,
  compared with just buying the S&P 500 on the same day; and whether higher-rated stocks really won more often.
- **Live record**: every morning's picks, saved permanently in `data/live/picks.csv` and scored against the S&P 500
  from the day they were made. Unlike the backtest, this can't be tuned after the fact: it is the real test.
- **Stock lookup**: every current S&P 500 member ranked by today's score. Search a ticker or company (or open
  `#lookup:AAPL`) to see its rank, risk, where it stands on each of the six measures and what stands out.
- **News on each stock**: `newsmatch.py` tags every headline with the S&P 500 companies it names (by name, well-known
  short name or ticker). Each pick shows its latest headline, each stock's dropdown lists its last two weeks of news, and
  the news page marks which companies a story is about and can show only portfolio holdings.
- **Market news** and **How it works**.

Holding periods and number of picks are `PICK_HORIZONS` and `N_PICKS` in `config.py`.

## Market news

```bash
python news.py          # collect today's headlines and rebuild the website
python news.py --open   # same, then open the news tab in your browser
```

Pulls headlines from MarketWatch, WSJ, CNBC, Bloomberg, FT, Seeking Alpha, Investing.com,
Google News, the Federal Reserve, the SEC, and Yahoo headlines for the tickers in `WATCHLIST`.
- `data/news/headlines.csv`: every headline ever collected. Nothing is deleted, so this becomes the
  news history to test a news feature on later. Feeds only keep a few days, so run it daily.

Change sources, the watchlist and how many days the page shows in `config.py`.

**Runs automatically in the cloud** (`.github/workflows/update.yml`). Every morning at 11:00 UTC (6-7 AM New York,
before the market opens) GitHub collects headlines, downloads the latest closing prices, retrains the model on
everything up to then, remakes the picks and publishes the website. Then, every hour until about 8 PM New York time,
it collects new headlines and republishes. Your Mac doesn't need to be on.
- Run it now: on GitHub, open **Actions → Daily update → Run workflow**.
- Get the latest headlines onto your Mac before working with them: `git pull`.
- Don't commit a `news.py` run made on your Mac; it would clash with the cloud's copy of `headlines.csv`.
  If you ran it locally, throw that away with `git checkout data/news outputs/news.html` before `git pull`.

## Testing new ideas fairly

```bash
python experiments.py                                  # test every candidate signal one at a time
python experiments.py --combo earnings_momentum        # test one or several together
python experiments.py --industry                       # rank the financials within each industry
```

Candidate signals live in `CANDIDATE_BUILDERS` in `features.py`. Each one is added to the current model and replayed
on 2016-2022 for every holding period and quarterly start month (12 results). It only **passes** if it beats the
current model in at least 9 of the 12 and by at least 0.2 points per period on average. Only passing signals should be
moved into `FUNDAMENTAL_BUILDERS`. Don't lower the bar after seeing results: that is how backtests end up fitting noise.

**Machine learning vs a simple score (Nov 2026):** a plain average of the six ranked financial measures beat the
random forest by 0.76 points per holding period (ahead in 7 of 12 results), so `MODEL_TYPE = "simple"` is now the
default; the rule, set before the test, was that ties go to the simpler method. The live record notes which model
made each pick (`model` column; picks from Nov 2, 2026 came from the random forest).

First round (Nov 2026): asset growth, profitability change, margin change, share buybacks, accruals, cash
profitability, earnings momentum and ranking within industry. **None passed**; results in `outputs/experiments.csv`.

## Where to tweak

| File | What it controls |
|---|---|
| `config.py` | stock universe (historical or today's list), which inputs to use (`USE_FUNDAMENTALS`, `USE_PRICE_FEATURES`), dates, horizon, top-fraction, trading costs, model settings |
| `features.py` | the inputs the model sees. Add a function plus one line in `FEATURE_BUILDERS` (prices) or `FUNDAMENTAL_BUILDERS` (financials) |
| `fundamentals.py` | company financials from SEC filings, lined up by when they were published |
| `backtest.py` | walk-forward training and the scorecard |
| `picks.py` | today's top picks and the fundamentals shown |
| `data.py` | downloading and caching prices and past S&P 500 membership |
| `news.py` | the news collector |
| `forecast.py` | today's picks per holding period, risk estimates and track record |
| `dashboard.py` | the website |
| `experiments.py` | the fair test for new signals |

## Ideas to try next
1. Change `TOP_FRACTION` (0.1, 0.3) and `HORIZON_MONTHS` (6, 24, 36).
2. Add features in `features.py` (e.g. 3-month momentum, price vs 200-day average).
3. Swap the model in `backtest.make_model()` (try `GradientBoostingClassifier`).
4. Set `UNIVERSE = "today"` and compare with `"historical"` to see how much survivorship bias inflates results.
5. Add more financials in `fundamentals.py` (`ITEMS`) and new ratios in `features.py`.

## Limitations (read these)
- **Survivorship bias (reduced, not gone):** by default the backtest uses the S&P 500 as it actually was on each date
  (membership history from github.com/fja05680/sp500), so stocks later dropped from the index are included.
  But Yahoo Finance has no prices for many companies that went bust, were bought out or changed ticker.
  The run prints how many real members are covered. The missing ones are mostly not random, so results can still be off.
- **Negative equity:** companies whose buybacks pushed book value below zero (e.g. McDonald's) get a neutral
  book-to-market instead of a misleading one, and are flagged on the website.
- **Reused tickers:** if a ticker was later given to a different company, Yahoo returns the new company's prices.
- **No untouched years left:** 2023 onward was held out, scored once with `python holdout.py` (Nov 3, 2026), and
  size weighting was adopted after studying it. Every past year has now shaped the model, so the live record
  is the only honest test from here on.
- **SEC financials are approximate:** the SEC's frames data holds each company's latest reported figure, so a
  later restatement can leak in. Numbers count as published 3-4 months after the period ends (a safe guess,
  not the real filing date). Market value is estimated from the public float, which leaves out insiders' shares.
- **Small sample:** about 10 yearly results. One great or terrible year means little.
- **Simplified costs, no taxes.**
- Beating the S&P 500 is hard. "No edge" is a normal, honest result.
- If you tune settings until the backtest looks great, you are fitting to the past. Always keep a final period you never tune on.
