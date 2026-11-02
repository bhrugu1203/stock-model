"""Turn prices into model inputs ("features") and the target we predict.

To add a new feature: write a function that takes the monthly price table and
returns a table of the same shape, then add it to FEATURE_BUILDERS. Features built
from company financials take (prices, financials) and go in FUNDAMENTAL_BUILDERS.
"""
import pandas as pd

import config


def _mom_12_1(m):   return m.shift(1) / m.shift(12) - 1          # 12-month momentum, skip last month
def _mom_6(m):      return m / m.shift(6) - 1                    # 6-month momentum
def _mom_1(m):      return m / m.shift(1) - 1                    # last-month return (reversal)
def _vol_12(m):     return m.pct_change().rolling(12).std()      # 12-month volatility
def _from_high(m):  return m / m.rolling(12).max() - 1           # distance below 12-month high


FEATURE_BUILDERS = {
    "mom_12_1": _mom_12_1,
    "mom_6": _mom_6,
    "mom_1": _mom_1,
    "vol_12": _vol_12,
    "from_high": _from_high,
}


# f is the dict from fundamentals.build(): tables of what each company had reported by each date
def _earnings_yield(m, f):   return f["net_income"] / f["market_cap"]               # cheap vs profits (E/P)
def _book_to_market(m, f):   return f["equity"].where(f["equity"] > 0) / f["market_cap"]  # cheap vs net worth
                                                     # (negative equity, e.g. from big buybacks, means nothing here)
def _gross_prof(m, f):       return f["gross_profit"] / f["assets"]                 # quality: gross profit per $ of assets
def _roa(m, f):              return f["net_income"] / f["assets"]                   # return on assets
def _rev_growth(m, f):       return f["revenue_growth"]                             # sales growth vs prior year
def _leverage(m, f):         return f["liabilities"].fillna(f["assets"] - f["equity"]) / f["assets"]


FUNDAMENTAL_BUILDERS = {
    "earnings_yield": _earnings_yield,
    "book_to_market": _book_to_market,
    "gross_prof": _gross_prof,
    "roa": _roa,
    "rev_growth": _rev_growth,
    "leverage": _leverage,
}


# --- Candidate signals: tested by experiments.py, moved into FUNDAMENTAL_BUILDERS only if they pass ---
def _yoy(t):                 return t.shift(12)                                     # what was known a year earlier
def _asset_growth(m, f):     return f["assets"] / _yoy(f["assets"]) - 1            # fast-expanding firms tend to lag
def _roa_change(m, f):       return _roa(m, f) - _yoy(_roa(m, f))                   # is profitability improving?
def _margin(f):              return f["gross_profit"] / f["revenue"]
def _margin_change(m, f):    return _margin(f) - _yoy(_margin(f))                   # are margins widening?
def _share_change(m, f):                                                            # buybacks (-) vs new shares (+)
    chg = f["shares"] / _yoy(f["shares"]) - 1
    return chg.where(chg.abs() < 0.35)                                              # bigger jumps are usually stock splits
def _accruals(m, f):         return (f["net_income"] - f["op_cash_flow"]) / f["assets"]  # profits not backed by cash
def _cash_profit(m, f):      return f["op_cash_flow"] / f["assets"]                 # cash generated per $ of assets
def _earnings_momentum(m, f): return (f["net_income_q"] - _yoy(f["net_income_q"])) / f["assets"]  # latest quarter vs a year ago


CANDIDATE_BUILDERS = {
    "asset_growth": _asset_growth,
    "roa_change": _roa_change,
    "margin_change": _margin_change,
    "share_change": _share_change,
    "accruals": _accruals,
    "cash_profit": _cash_profit,
    "earnings_momentum": _earnings_momentum,
}


def _rank(raw, members, groups=None):
    """Percentile rank across stocks on each date; within each industry group if groups is given."""
    raw = raw.where(members)
    if groups is None:
        return raw.rank(axis=1, pct=True)
    g = groups.reindex(raw.columns).fillna("Unknown")
    return raw.T.groupby(g).rank(pct=True).T


def build_panel(monthly, members=None, fundamentals=None, builders=None, groups=None):
    """Return (panel, feature_names). panel has one row per (date, ticker) with
    rank-normalised features and 'fwd_rel' = next-N-month return minus the median stock.
    Only stocks that were index members on that date (members table) get a row.
    builders: financial features to use (default FUNDAMENTAL_BUILDERS).
    groups: ticker -> industry; if given, financial features are ranked within each industry."""
    if members is None:
        members = monthly.notna()
    feats = {k: f(monthly).where(members) for k, f in FEATURE_BUILDERS.items()}
    ranked = {k: v.rank(axis=1, pct=True) for k, v in feats.items()}
    builders = FUNDAMENTAL_BUILDERS if builders is None else builders
    if fundamentals is not None:
        for k, fn in builders.items():
            raw = fn(monthly, fundamentals).replace([float("inf"), float("-inf")], float("nan"))
            # a missing financial (e.g. banks report no gross profit) counts as middle of the pack
            ranked[k] = _rank(raw, members, groups).fillna(0.5).where(members)

    h = config.HORIZON_MONTHS
    # carry the last price forward so a stock that is bought out or delisted keeps its
    # final value instead of silently vanishing from the results
    fwd = (monthly.ffill().shift(-h) / monthly - 1).where(members)
    fwd_rel = fwd.sub(fwd.median(axis=1), axis=0)

    panel = pd.DataFrame({**{k: v.stack() for k, v in ranked.items()},
                          "fwd_rel": fwd_rel.stack()})
    panel.index.names = ["date", "ticker"]
    panel = panel.dropna(subset=list(FEATURE_BUILDERS))
    names = list(ranked)
    if fundamentals is not None and not config.USE_PRICE_FEATURES:
        # price features stay in the panel (the momentum benchmark uses them) but the model skips them
        names = list(builders)
    return panel, names
