"""Downloading and caching price data and S&P 500 membership."""
import io
import os

import numpy as np
import pandas as pd

import config

# Point-in-time S&P 500 member lists since 1996, maintained at github.com/fja05680/sp500
HISTORY_URL = ("https://raw.githubusercontent.com/fja05680/sp500/master/"
               "S%26P%20500%20Historical%20Components%20%26%20Changes%20(Updated).csv")


def get_sp500_tickers():
    import requests
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    table = pd.read_html(io.StringIO(html))[0]
    return [t.replace(".", "-") for t in table["Symbol"].tolist()]


def get_sp500_history(refresh=False):
    """Return a Series: date -> list of tickers in the S&P 500 from that date on."""
    path = os.path.join(config.CACHE_DIR, "sp500_history.csv")
    if refresh or not os.path.exists(path):
        import requests
        resp = requests.get(HISTORY_URL, timeout=30)
        resp.raise_for_status()
        with open(path, "w") as f:
            f.write(resp.text)
    hist = pd.read_csv(path, parse_dates=["date"]).set_index("date")["tickers"]
    return hist.str.replace(".", "-", regex=False).str.split(",")


def _month_end(df):
    try:
        monthly = df.resample("ME").last()
    except ValueError:  # older pandas
        monthly = df.resample("M").last()
    # the current month is unfinished: label it with the last real trading day, not the month end
    last = min(monthly.index[-1], df.index[-1])
    return monthly.rename(index={monthly.index[-1]: last})


def _download(tickers):
    import yfinance as yf
    raw = yf.download(tickers, start=config.START_DATE, auto_adjust=True, progress=False)["Close"]
    # yfinance sometimes fails a few tickers when downloading in parallel; retry those one by one
    missing = [t for t in tickers if t not in raw.columns or raw[t].isna().all()]
    if missing:
        retry = yf.download(missing, start=config.START_DATE, auto_adjust=True,
                            progress=False, threads=False)["Close"]
        if isinstance(retry, pd.Series):
            retry = retry.to_frame(missing[0])
        raw = raw.drop(columns=[t for t in missing if t in raw.columns]).join(retry, how="outer")
    return raw


def membership(monthly, history):
    """True where a ticker was in the S&P 500 on that month's date."""
    snap = history.reindex(monthly.index, method="ffill")
    return pd.DataFrame({d: monthly.columns.isin(t) for d, t in snap.items()},
                        index=monthly.columns).T


def load_prices(refresh=False):
    """Return (monthly stock prices, monthly SPY prices, members). members is a True/False table
    of who was in the index on each date. Cached in data/ so tweaking the model does not
    re-download every time. Use refresh=True to re-download."""
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    if config.UNIVERSE == "historical":
        name = f"prices_historical_{config.START_DATE}.csv"
    else:
        name = f"prices_{config.N_STOCKS}_{config.SAMPLE_SEED}_{config.START_DATE}.csv"
    path = os.path.join(config.CACHE_DIR, name)

    if config.UNIVERSE == "historical":
        history = get_sp500_history(refresh=refresh)

    if os.path.exists(path) and not refresh:
        monthly_all = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        if config.UNIVERSE == "historical":
            since = history[history.index >= config.START_DATE]
            earlier = history[history.index < config.START_DATE]
            if len(earlier):
                since = pd.concat([earlier.iloc[-1:], since])
            tickers = sorted(set().union(*since))
        else:
            all_tickers = get_sp500_tickers()
            rng = np.random.RandomState(config.SAMPLE_SEED)
            n = min(config.N_STOCKS, len(all_tickers))
            tickers = list(rng.choice(all_tickers, size=n, replace=False))
        print(f"Downloading {len(tickers)} stocks + SPY from Yahoo Finance "
              f"({'several minutes' if len(tickers) > 300 else 'about a minute'})...")
        monthly_all = _month_end(_download(tickers + ["SPY"]))
        monthly_all.to_csv(path)
        print("Saved to", path)

    spy = monthly_all["SPY"]
    monthly = monthly_all.drop(columns="SPY")
    if config.UNIVERSE == "historical":
        monthly = monthly.dropna(axis=1, how="all")
        return monthly, spy, membership(monthly, history)
    monthly = monthly.dropna(axis=1, thresh=int(len(monthly) * 0.8))
    return monthly, spy, monthly.notna()


def coverage(monthly, members, history):
    """Share of each date's real index members that we actually have prices for."""
    snap = history.reindex(members.index, method="ffill")
    return (members & monthly.notna()).sum(axis=1) / snap.str.len()


def synthetic_prices(seed=1, n_stocks=80):
    """Random-walk fake prices, for testing the pipeline offline. Results are meaningless."""
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2010-01-31", "2026-10-31", freq="ME")
    cols = [f"T{i}" for i in range(n_stocks)]
    prices = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0.007, 0.07, (len(idx), n_stocks)), axis=0)),
        index=idx, columns=cols)
    spy = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.008, 0.04, len(idx)))), index=idx)
    # fake index changes: each fake stock is a member for a random stretch of years
    start = rng.randint(0, len(idx) // 2, n_stocks)
    end = start + rng.randint(len(idx) // 3, len(idx), n_stocks)
    pos = np.arange(len(idx))[:, None]
    members = pd.DataFrame((pos >= start) & (pos < end), index=idx, columns=cols)
    return prices, spy, members
