"""Walk-forward backtest: train only on outcomes already known, then trade."""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

import config


def make_model():
    return RandomForestClassifier(**config.MODEL_PARAMS)


def run_backtest(monthly, spy, panel, feature_names, final=False):
    """Score each rebalance year. Years from config.HOLDOUT_FROM_YEAR on are skipped
    unless final=True, so they stay untouched while you tune."""
    h = config.HORIZON_MONTHS
    dates = monthly.index
    prices = monthly.ffill()   # a delisted or bought-out stock keeps its last price
    date_level = panel.index.get_level_values("date")
    rows, last_model = [], None

    for i in range(len(dates) - h):
        d = dates[i]
        if d.year < config.FIRST_TEST_YEAR or d.month != config.REBALANCE_MONTH:
            continue
        if d.year >= config.HOLDOUT_FROM_YEAR and not final:
            continue

        cutoff = dates[i - h]   # outcomes up to here were fully known on date d
        train = panel[(date_level <= cutoff) & panel["fwd_rel"].notna()]
        test = panel[date_level == d]
        if len(train) < 500 or len(test) < 20:
            continue

        model = make_model()
        model.fit(train[feature_names], (train["fwd_rel"] > 0).astype(int))
        last_model = model

        prob = pd.Series(model.predict_proba(test[feature_names])[:, 1],
                         index=test.index.get_level_values("ticker"))
        n_pick = max(1, int(len(prob) * config.TOP_FRACTION))
        model_picks = prob.nlargest(n_pick).index
        mom_picks = test["mom_12_1"].droplevel("date").nlargest(n_pick).index

        realized = (prices.iloc[i + h] / monthly.iloc[i] - 1)[prob.index]
        rows.append({
            "date": d,
            "ML model": realized[model_picks].mean() - config.COST_PER_REBALANCE,
            "Momentum only": realized[mom_picks].mean() - config.COST_PER_REBALANCE,
            "Average stock": realized.dropna().mean(),
            "S&P 500 (SPY)": spy.iloc[i + h] / spy.iloc[i] - 1,
        })

    res = pd.DataFrame(rows).set_index("date")
    res.index = res.index.year
    return res, last_model


def scorecard(res):
    growth = (1 + res).cumprod()
    n = len(res)
    return growth, pd.DataFrame({
        "CAGR %": (growth.iloc[-1] ** (1 / n) - 1) * 100,
        "Worst year %": res.min() * 100,
        "Win rate vs SPY %": [(res[c] > res["S&P 500 (SPY)"]).mean() * 100 for c in res.columns],
    }).round(1)
