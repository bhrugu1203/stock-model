"""Turn prices into model inputs ("features") and the target we predict.

To add a new feature: write a function that takes the monthly price table and
returns a table of the same shape, then add it to FEATURE_BUILDERS.
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


def build_panel(monthly, members=None):
    """Return (panel, feature_names). panel has one row per (date, ticker) with
    rank-normalised features and 'fwd_rel' = next-N-month return minus the median stock.
    Only stocks that were index members on that date (members table) get a row."""
    if members is None:
        members = monthly.notna()
    feats = {k: f(monthly).where(members) for k, f in FEATURE_BUILDERS.items()}
    ranked = {k: v.rank(axis=1, pct=True) for k, v in feats.items()}

    h = config.HORIZON_MONTHS
    # carry the last price forward so a stock that is bought out or delisted keeps its
    # final value instead of silently vanishing from the results
    fwd = (monthly.ffill().shift(-h) / monthly - 1).where(members)
    fwd_rel = fwd.sub(fwd.median(axis=1), axis=0)

    panel = pd.DataFrame({**{k: v.stack() for k, v in ranked.items()},
                          "fwd_rel": fwd_rel.stack()})
    panel.index.names = ["date", "ticker"]
    names = list(FEATURE_BUILDERS)
    panel = panel.dropna(subset=names)
    return panel, names
