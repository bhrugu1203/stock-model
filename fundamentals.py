"""Company financials from SEC filings (the free XBRL "frames" API at data.sec.gov).

Each number only becomes visible to the model a few months after the period it
describes ends, roughly when the company would have filed it. That keeps the
backtest from using information nobody had yet.
"""
import os
import time

import numpy as np
import pandas as pd

import config

FRAMES_URL = "https://data.sec.gov/api/xbrl/frames/{tax}/{tag}/USD/{period}.json"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_DIR = os.path.join(config.CACHE_DIR, "sec")

# name: (taxonomy, tags to try in order, "annual" or "instant", months until it counts as published)
ITEMS = {
    "revenue":      ("us-gaap", ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                                 "SalesRevenueNet"], "annual", 4),
    "net_income":   ("us-gaap", ["NetIncomeLoss"], "annual", 4),
    "gross_profit": ("us-gaap", ["GrossProfit"], "annual", 4),
    # many companies never report a gross profit line; revenue minus this fills the gap
    "cost_of_revenue": ("us-gaap", ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
                        "annual", 4),
    "assets":       ("us-gaap", ["Assets"], "instant", 3),
    "equity":       ("us-gaap", ["StockholdersEquity"], "instant", 3),
    "liabilities":  ("us-gaap", ["Liabilities"], "instant", 3),
    # market value of shares held by outsiders, measured mid-year and reported in the annual report
    "public_float": ("dei", ["EntityPublicFloat"], "instant", 10),
}
MAX_AGE_MONTHS = 24   # ignore numbers older than this (company stopped filing)


def _get(url):
    import requests
    for attempt in range(3):
        r = requests.get(url, headers={"User-Agent": config.SEC_USER_AGENT}, timeout=60)
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            return r.json()
        time.sleep(2 + 3 * attempt)
    r.raise_for_status()


def _periods(kind):
    first, last = int(config.START_DATE[:4]) - 1, pd.Timestamp.today().year
    if kind == "annual":
        return [f"CY{y}" for y in range(first, last)]
    return [f"CY{y}Q{q}I" for y in range(first, last + 1) for q in range(1, 5)]


def download(items=None):
    """Fetch the given items (default: all) for every company as one long table: item, cik, end, value."""
    rows = []
    for name in items or ITEMS:
        tax, tags, kind, _ = ITEMS[name]
        print(f"  SEC: {name}")
        for rank, tag in enumerate(tags):
            for period in _periods(kind):
                d = _get(FRAMES_URL.format(tax=tax, tag=tag, period=period))
                time.sleep(0.12)   # the SEC allows at most 10 requests a second
                for rec in (d or {}).get("data", []):
                    rows.append((name, rank, rec["cik"], rec["end"], rec["val"]))
    df = pd.DataFrame(rows, columns=["item", "rank", "cik", "end", "value"])
    # if several tags report the same thing, keep the preferred one
    df = df.sort_values("rank").drop_duplicates(["item", "cik", "end"]).drop(columns="rank")
    return df


def ticker_table():
    """Today's ticker -> SEC company number (cik) and company name."""
    import requests
    data = requests.get(TICKERS_URL, headers={"User-Agent": config.SEC_USER_AGENT}, timeout=60).json()
    rows = [(v["ticker"].replace(".", "-"), v["cik_str"], v["title"]) for v in data.values()]
    return pd.DataFrame(rows, columns=["ticker", "cik", "name"]).drop_duplicates("ticker").set_index("ticker")


def _ticker_map(refresh=False):
    path = os.path.join(SEC_DIR, "ticker_cik.csv")
    if not refresh and os.path.exists(path):
        table = pd.read_csv(path, index_col="ticker")
        if "name" in table.columns:
            return table
    table = ticker_table()
    table.to_csv(path)
    return table


def company_names():
    return _ticker_map()["name"]


def load_raw(refresh=False):
    os.makedirs(SEC_DIR, exist_ok=True)
    facts_path = os.path.join(SEC_DIR, "facts.csv")
    if refresh or not os.path.exists(facts_path):
        print("Downloading company financials from the SEC (a few minutes)...")
        download().to_csv(facts_path, index=False)
    facts = pd.read_csv(facts_path, parse_dates=["end"])
    missing = [name for name in ITEMS if name not in set(facts["item"])]
    if missing:   # an item was added to ITEMS since the last download
        print(f"Downloading new SEC items: {', '.join(missing)}...")
        new = download(missing)
        new["end"] = pd.to_datetime(new["end"])
        facts = pd.concat([facts, new], ignore_index=True)
        facts.to_csv(facts_path, index=False)
    facts = _add_gross_profit(facts)
    return facts, _ticker_map(refresh)["cik"]


def _add_gross_profit(facts):
    """Where a company reported no gross profit, use revenue minus cost of revenue for the same period."""
    key = ["cik", "end"]
    rev = facts[facts["item"] == "revenue"][key + ["value"]]
    cost = facts[facts["item"] == "cost_of_revenue"][key + ["value"]]
    derived = rev.merge(cost, on=key, suffixes=("_rev", "_cost"))
    derived = derived.assign(item="gross_profit", value=derived["value_rev"] - derived["value_cost"])[
        ["item"] + key + ["value"]]
    reported = facts[facts["item"] == "gross_profit"].set_index(key).index
    derived = derived[~derived.set_index(key).index.isin(reported)]
    return pd.concat([facts, derived], ignore_index=True)


def _known_on(dates, ends, values, lag):
    """Value of the most recent record already published on each date (NaN if none, or too old)."""
    if len(ends) == 0:
        return np.full(len(dates), np.nan), np.full(len(dates), np.datetime64("NaT"), dtype="datetime64[ns]")
    s = pd.DataFrame({"end": ends, "value": values}).sort_values("end")
    s["available"] = s["end"] + pd.DateOffset(months=lag)
    s = s.sort_values(["available", "end"]).drop_duplicates("available", keep="last")
    idx = s["available"].searchsorted(dates, side="right") - 1
    ok = idx >= 0
    val = np.where(ok, s["value"].to_numpy()[idx.clip(0)], np.nan)
    end = np.where(ok, s["end"].to_numpy()[idx.clip(0)], np.datetime64("NaT"))
    too_old = (dates.to_numpy() - end) > np.timedelta64(MAX_AGE_MONTHS * 31, "D")
    val[too_old] = np.nan
    return val, end


def build(monthly, refresh=False):
    """Return {name: table shaped like monthly} of what was known on each date.
    Includes the raw items plus 'revenue_growth' and 'market_cap' (estimated)."""
    facts, cik = load_raw(refresh)
    dates = monthly.index
    out = {name: pd.DataFrame(np.nan, index=dates, columns=monthly.columns)
           for name in list(ITEMS) + ["revenue_growth", "market_cap"]}
    facts = facts[facts["cik"].isin(set(cik.reindex(monthly.columns).dropna()))]
    by_key = {k: g for k, g in facts.groupby(["item", "cik"])}
    coverage = 0
    for t in monthly.columns:
        if t not in cik.index:
            continue
        c = cik[t]
        coverage += 1
        for name, (_, _, _, lag) in ITEMS.items():
            g = by_key.get((name, c))
            if g is None:
                continue
            val, end = _known_on(dates, g["end"], g["value"].to_numpy(dtype=float), lag)
            out[name][t] = val
            if name == "revenue":
                g = g.sort_values("end")
                prev = g["value"].shift(1)
                gap = (g["end"] - g["end"].shift(1)).dt.days
                growth = (g["value"] / prev - 1).where(gap.between(330, 400) & (prev > 0))
                out["revenue_growth"][t], _ = _known_on(dates, g["end"], growth.to_numpy(dtype=float), lag)
            if name == "public_float":
                # float was measured on its own date; grow it with the share price since then
                price = monthly[t]
                p_then = price.reindex(pd.DatetimeIndex(end), method="ffill").to_numpy()
                out["market_cap"][t] = val * price.to_numpy() / p_then
    print(f"SEC financials matched for {coverage} of {monthly.shape[1]} stocks "
          "(no match = old ticker the SEC no longer lists)")
    return out


def synthetic(monthly, seed=2):
    """Random fake financials for the offline demo and smoke test."""
    rng = np.random.RandomState(seed)
    shape = monthly.shape
    f = {name: pd.DataFrame(rng.lognormal(20, 1, shape), index=monthly.index, columns=monthly.columns)
         for name in ITEMS}
    f["revenue_growth"] = pd.DataFrame(rng.normal(0.05, 0.1, shape), index=monthly.index, columns=monthly.columns)
    f["market_cap"] = f["public_float"]
    return f
