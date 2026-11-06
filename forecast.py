"""Today's picks for several holding periods, each with an honest track record:  python forecast.py

For every holding period in config.PICK_HORIZONS (e.g. 6, 12, 24 months) this:
  1. replays the model on past dates it had never seen (walk-forward), to show whether
     following its picks would have beaten simply buying the S&P 500;
  2. checks how often stocks the model rated highly actually beat the typical stock;
  3. trains on all history and lists today's top picks, with a risk estimate for each.
  4. adds today's picks to the live record (live.py) and scores every earlier pick.
Results go to outputs/forecast.json, which dashboard.py turns into the website.
"""
import argparse
import json
import math
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config
import data
import fundamentals
import live
from backtest import SIMPLE_DIRECTIONS, SimpleScore, make_model
from features import build_panel

OUT = os.path.join(config.OUTPUT_DIR, "forecast.json")
START_MONTHS = [1, 4, 7, 10]   # track record: a new set of picks every quarter
MARKET_DRIFT = 0.08             # assumed long-run yearly stock return, used for the risk range
TRAITS = {                      # plain-English labels for a stock that ranks in the top or bottom 15%
    "earnings_yield": ("Cheap vs. earnings", "Expensive vs. earnings"),
    "book_to_market": ("Cheap vs. book value", "Expensive vs. book value"),
    "gross_prof":     ("Highly profitable business", "Low gross profitability"),
    "roa":            ("Strong return on assets", "Weak return on assets"),
    "rev_growth":     ("Fast revenue growth", "Shrinking or slow revenue"),
    "leverage":       ("Heavy debt load", "Low debt"),
}


def horizon_label(h):
    return f"{h} months" if h < 12 else ("1 year" if h == 12 else f"{h // 12} years")


def _risk(prices, h):
    """Volatility-based outcome range and chance of loss over h months, plus the stock's own history."""
    p = prices.dropna()
    vol = p.pct_change().dropna().tail(36).std() * math.sqrt(12)
    t = h / 12
    mu = (MARKET_DRIFT - vol ** 2 / 2) * t
    sd = vol * math.sqrt(t)
    low, high = math.exp(mu - 1.2816 * sd) - 1, math.exp(mu + 1.2816 * sd) - 1   # 80% range
    p_loss = 0.5 * (1 + math.erf(-mu / (sd * math.sqrt(2)))) if sd > 0 else 0.0
    past = (p.shift(-h) / p - 1).dropna()
    return {"volatility": round(vol, 3), "range_low": round(low, 3), "range_high": round(high, 3),
            "chance_of_loss": round(p_loss, 3),
            "hist_chance_of_loss": round(float((past < 0).mean()), 3) if len(past) >= 12 else None}


def weights(size, date, tickers):
    """How much of the portfolio goes in each stock: by company value (config.WEIGHTING = "size")
    or the same for each. A company with no size estimate gets the median size of the others."""
    if config.WEIGHTING != "size" or size is None:
        return pd.Series(1 / len(tickers), index=tickers)
    w = size.loc[date].reindex(tickers)
    w = w.where(w > 0).fillna(w[w > 0].median() if (w > 0).any() else 1.0)
    return w / w.sum()


def track_record(monthly, spy, panel, names, h, holdout=False, size=None):
    """Walk-forward replay. Refit each January on outcomes already known, pick every quarter,
    and only use outcomes that ended before the held-out years. holdout=True instead replays
    only picks made in the held-out years (holdout.py, run once)."""
    dates, prices = monthly.index, monthly.ffill()
    date_level = panel.index.get_level_values("date")
    holdout_start = pd.Timestamp(f"{config.HOLDOUT_FROM_YEAR}-02-01")
    periods, calib = [], []
    years = range(config.HOLDOUT_FROM_YEAR, dates[-1].year + 1) if holdout else \
        range(config.FIRST_TEST_YEAR, config.HOLDOUT_FROM_YEAR)
    for year in years:
        jan = [i for i, d in enumerate(dates) if d.year == year and d.month == 1]
        if not jan or jan[0] < h:
            continue
        cutoff = dates[jan[0] - h]
        train = panel[(date_level <= cutoff) & panel["fwd_rel"].notna()]
        if len(train) < 500:
            continue
        model = make_model().fit(train[names], (train["fwd_rel"] > 0).astype(int))
        for i, d in enumerate(dates):
            if d.year != year or d.month not in START_MONTHS or i + h >= len(dates):
                continue
            if dates[i + h] >= holdout_start and not holdout:
                continue
            test = panel[date_level == d].droplevel("date")
            if len(test) < 20:
                continue
            prob = pd.Series(model.predict_proba(test[names])[:, 1], index=test.index)
            realized = (prices.iloc[i + h] / monthly.iloc[i] - 1)[test.index]
            spy_ret = float(spy.iloc[i + h] / spy.iloc[i] - 1)
            picks = prob.nlargest(max(1, int(len(prob) * config.TOP_FRACTION))).index
            w = weights(size, d, picks)[realized[picks].notna()]
            pick_ret = float((realized[w.index] * w).sum() / w.sum() - config.COST_PER_REBALANCE)
            periods.append({"start": d.strftime("%Y-%m"), "end": dates[i + h].strftime("%Y-%m"),
                            "picks": round(pick_ret, 4), "average_stock": round(float(realized.mean()), 4),
                            "sp500": round(spy_ret, 4),
                            "pick_wins": int((realized[picks] > spy_ret).sum()), "pick_count": len(picks)})
            calib.append(pd.DataFrame({"pct": prob.rank(pct=True),
                                       "beat": realized > realized.median()}))
    calib = pd.concat(calib) if calib else pd.DataFrame(columns=["pct", "beat"])
    bins = pd.cut(calib["pct"], [0, .2, .4, .6, .8, 1.0], labels=["Bottom 20%", "20-40%", "40-60%", "60-80%", "Top 20%"])
    calibration = [{"bucket": str(b), "hit_rate": round(float(g["beat"].mean()), 3), "n": int(len(g))}
                   for b, g in calib.groupby(bins, observed=True)]
    return periods, calibration


def summarize(periods):
    if not periods:
        return {}
    df = pd.DataFrame(periods)
    return {
        "periods": len(df),
        "beat_sp500": int((df["picks"] > df["sp500"]).sum()),
        "beat_average_stock": int((df["picks"] > df["average_stock"]).sum()),
        "avg_picks": round(float(df["picks"].mean()), 4),
        "avg_sp500": round(float(df["sp500"].mean()), 4),
        "avg_average_stock": round(float(df["average_stock"].mean()), 4),
        "pick_wins": int(df["pick_wins"].sum()), "pick_losses": int((df["pick_count"] - df["pick_wins"]).sum()),
        "first": df["start"].iloc[0], "last": df["end"].iloc[-1],
    }


def _traits(now, fund, t):
    traits = []
    for k, (hi, lo) in TRAITS.items():
        if k in now.columns and now.at[t, k] != 0.5:      # 0.5 = not reported
            if now.at[t, k] >= 0.85:
                traits.append(hi)
            elif now.at[t, k] <= 0.15:
                traits.append(lo)
    if fund["equity"][t].iloc[-1] <= 0:
        traits.append("Negative book value")
    return traits


def todays_picks(monthly, fund, panel, names, h):
    """Today's portfolio (the top 20% by score, biggest holdings first), plus today's score for
    every current member (for the stock lookup)."""
    train = panel[panel["fwd_rel"].notna()]
    model = make_model().fit(train[names], (train["fwd_rel"] > 0).astype(int))
    latest = monthly.index[-1]
    now = panel[panel.index.get_level_values("date") == latest].droplevel("date")
    prob = pd.Series(model.predict_proba(now[names])[:, 1], index=now.index)
    pct = prob.rank(pct=True)
    company = fundamentals.company_names()
    held = prob.nlargest(max(1, int(len(prob) * config.TOP_FRACTION))).index
    w = weights(fund.get("size"), latest, held).sort_values(ascending=False, kind="stable")
    order = prob.rank(ascending=False, method="min")
    picks = []
    for rank, t in enumerate(w.index, 1):
        picks.append({"rank": rank, "ticker": t, "name": str(company.get(t, "")).title(),
                      "weight": round(float(w[t]), 4), "score_rank": int(order[t]),
                      "probability": round(float(prob[t]), 3), "percentile": round(float(pct[t]), 3),
                      "price": round(float(monthly[t].dropna().iloc[-1]), 2),
                      "traits": _traits(now, fund, t), **_risk(monthly[t], h)})
    importance = sorted(zip(names, model.feature_importances_), key=lambda x: -x[1])
    return picks, [{"feature": k, "importance": round(float(v), 3)} for k, v in importance], prob, now


def all_stocks(monthly, fund, now, names, scores, held):
    """One row per current S&P 500 member: its score, rank and risk for every holding period,
    and where it stands on each measure (0-1, higher = better; leverage is flipped so low debt scores high)."""
    company = fundamentals.company_names()
    industry = fundamentals.sectors(now.index)
    ranks = {h: (prob.rank(ascending=False, method="min"), prob.rank(pct=True)) for h, prob in scores.items()}
    rows = []
    for t in now.index:
        p = monthly[t].dropna()
        year_ago = p[p.index <= p.index[-1] - pd.DateOffset(months=12)]
        measures = {k: (None if now.at[t, k] == 0.5 else
                        round(float(now.at[t, k] if SIMPLE_DIRECTIONS.get(k, 1) > 0 else 1 - now.at[t, k]), 3))
                    for k in names}
        horizons = []
        for h, prob in scores.items():
            horizons.append({"months": h, "rank": int(ranks[h][0][t]), "score": round(float(prob[t]), 3),
                             "percentile": round(float(ranks[h][1][t]), 3), **_risk(monthly[t], h)})
        rows.append({"ticker": t, "name": str(company.get(t, "")).title(), "industry": industry.get(t, "Unknown"),
                     "price": round(float(p.iloc[-1]), 2),
                     "ret_1y": round(float(p.iloc[-1] / year_ago.iloc[-1] - 1), 4) if len(year_ago) else None,
                     "measures": measures, "traits": _traits(now, fund, t), "horizons": horizons,
                     "weight": held.get(t)})
    return sorted(rows, key=lambda r: r["horizons"][0]["rank"])


def cap_weights(w, cap):
    """Limit every weight to cap, handing the excess to the others in proportion to their weight."""
    w = w / w.sum()
    for _ in range(50):
        over = w > cap + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over & (w < cap)
        w[under] += excess * w[under] / w[under].sum()
    return w


def versions(panel, names, size, date, held):
    """Today's portfolio for each alternative in config.SHADOW_VERSIONS: {name: weights}."""
    out = {"main": held, "capped": cap_weights(held.copy(), config.SHADOW_CAP),
           "equal": pd.Series(1 / len(held), index=held.index)}
    now = panel[panel.index.get_level_values("date") == date].droplevel("date")
    extra = names + ["mom_12_1"]
    now = now.dropna(subset=extra)
    score = pd.Series(SimpleScore().fit(now[extra]).predict_proba(now[extra])[:, 1], index=now.index)
    top = score.nlargest(max(1, int(len(score) * config.TOP_FRACTION))).index
    out["momentum"] = weights(size, date, top)
    return {k: v.sort_values(ascending=False) for k, v in out.items() if k in config.SHADOW_VERSIONS}


def industry_mix(stocks, size, date):
    """Share of the portfolio and of the S&P 500 (by company value) in each industry, biggest first.
    Industries under 1% of both are grouped as "Other"."""
    tickers = [s["ticker"] for s in stocks]
    industry = pd.Series({s["ticker"]: s["industry"] for s in stocks})
    held = pd.Series({s["ticker"]: s["weight"] for s in stocks if s["weight"] is not None})
    index = weights(size, date, tickers)
    df = pd.DataFrame({"portfolio": held.groupby(industry[held.index]).sum(), "sp500": index.groupby(industry).sum()}).fillna(0)
    small = (df["portfolio"] < 0.01) & (df["sp500"] < 0.01)
    if small.sum() > 1:
        df = pd.concat([df[~small], pd.DataFrame({"portfolio": [df.loc[small, "portfolio"].sum()],
                                                  "sp500": [df.loc[small, "sp500"].sum()]}, index=["Other"])])
    top = held.sort_values(ascending=False)
    rows = []
    for name, r in df.sort_values(["portfolio", "sp500"], ascending=False).iterrows():
        members = [t for t in top.index if industry[t] == name] if name != "Other" else \
            [t for t in top.index if small.get(industry[t], False)]
        rows.append({"industry": name, "portfolio": round(float(r["portfolio"]), 4), "sp500": round(float(r["sp500"]), 4),
                     "holdings": members[:5], "n_holdings": len(members)})
    return sorted(rows, key=lambda r: (r["industry"] == "Other", -r["portfolio"], -r["sp500"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="fake data, offline (results meaningless)")
    ap.add_argument("--refresh-prices", action="store_true", help="re-download prices (the daily cloud run does this)")
    ap.add_argument("--no-record", action="store_true",
                    help="don't add today's picks to the live record (the cloud run keeps the official record)")
    args = ap.parse_args()

    if args.demo:
        monthly, spy, members = data.synthetic_prices()
        fund = fundamentals.synthetic(monthly)
    else:
        monthly, spy, members = data.load_prices(refresh=args.refresh_prices)
        fund = fundamentals.build(monthly)
    fund["size"] = fundamentals.company_size(monthly, fund)

    result = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "data_through": monthly.index[-1].strftime("%Y-%m-%d"), "demo": args.demo,
              "holdout_from": config.HOLDOUT_FROM_YEAR, "top_fraction": config.TOP_FRACTION,
              "market_drift": MARKET_DRIFT, "model": config.MODEL_TYPE, "weighting": config.WEIGHTING,
              "n_show": config.N_PICKS, "horizons": []}
    scores, panels = {}, {}
    for h in config.PICK_HORIZONS:
        print(f"Horizon {horizon_label(h)}...")
        config.HORIZON_MONTHS = h
        panel, names = build_panel(monthly, members, fund)
        panels[h] = panel
        periods, calibration = track_record(monthly, spy, panel, names, h, size=fund["size"])
        picks, importance, scores[h], now = todays_picks(monthly, fund, panel, names, h)
        universe = len(scores[h])
        result["horizons"].append({"months": h, "label": horizon_label(h), "universe": universe,
                                   "summary": summarize(periods), "periods": periods,
                                   "calibration": calibration, "picks": picks, "importance": importance})
        s = result["horizons"][-1]["summary"]
        if s:
            print(f"  beat S&P 500 in {s['beat_sp500']}/{s['periods']} periods; "
                  f"avg {s['avg_picks']:.1%} vs S&P {s['avg_sp500']:.1%}; top pick {picks[0]['ticker']}")

    held = {p["ticker"]: p["weight"] for p in result["horizons"][0]["picks"]}
    result["stocks"] = all_stocks(monthly, fund, now, names, scores, held)
    result["industry_mix"] = industry_mix(result["stocks"], fund["size"], monthly.index[-1])

    result["live"] = result["versions"] = None
    if not args.demo and not args.no_record:
        ledger = live.record(monthly.index[-1], result["horizons"], monthly, spy)
        result["live"] = live.scoreboard(ledger, monthly, spy, result["horizons"])
        h = config.SHADOW_MONTHS if config.SHADOW_MONTHS in panels else config.PICK_HORIZONS[-1]
        main = next(x for x in result["horizons"] if x["months"] == h)["picks"]
        held_w = pd.Series({p["ticker"]: p["weight"] for p in main})
        alts = versions(panels[h], names, fund["size"], monthly.index[-1], held_w)
        result["versions"] = live.versions_board(live.record_versions(monthly.index[-1], alts, monthly, spy), monthly, spy)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("Saved", OUT)


if __name__ == "__main__":
    main()
