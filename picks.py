"""Score the most recent month and list the model's current top picks."""
import pandas as pd

import config
from backtest import make_model


def current_picks(monthly, panel, feature_names, with_fundamentals=True):
    latest = monthly.index[-1]
    date_level = panel.index.get_level_values("date")
    train = panel[panel["fwd_rel"].notna()]
    model = make_model()
    model.fit(train[feature_names], (train["fwd_rel"] > 0).astype(int))

    now = panel[date_level == latest]
    scores = pd.Series(model.predict_proba(now[feature_names])[:, 1],
                       index=now.index.get_level_values("ticker"))
    top = scores.nlargest(max(1, int(len(scores) * config.TOP_FRACTION)))

    rows = []
    for t in top.index:
        info = {}
        if with_fundamentals:
            try:
                import yfinance as yf
                info = yf.Ticker(t).info
            except Exception:
                info = {}
        rows.append({
            "ticker": t,
            "model score": round(float(top[t]), 3),
            "trailing P/E": info.get("trailingPE"),
            "profit margin": info.get("profitMargins"),
            "debt/equity": info.get("debtToEquity"),
            "revenue growth": info.get("revenueGrowth"),
        })
    return latest, pd.DataFrame(rows).set_index("ticker")
