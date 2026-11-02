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


def build_panel(monthly, members=None, fundamentals=None):
    """Return (panel, feature_names). panel has one row per (date, ticker) with
    rank-normalised features and 'fwd_rel' = next-N-month return minus the median stock.
    Only stocks that were index members on that date (members table) get a row."""
    if members is None:
        members = monthly.notna()
    feats = {k: f(monthly).where(members) for k, f in FEATURE_BUILDERS.items()}
    ranked = {k: v.rank(axis=1, pct=True) for k, v in feats.items()}
    if fundamentals is not None:
        for k, fn in FUNDAMENTAL_BUILDERS.items():
            raw = fn(monthly, fundamentals).replace([float("inf"), float("-inf")], float("nan"))
            # a missing financial (e.g. banks report no gross profit) counts as middle of the pack
            ranked[k] = raw.where(members).rank(axis=1, pct=True).fillna(0.5).where(members)

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
        names = list(FUNDAMENTAL_BUILDERS)
    return panel, names
