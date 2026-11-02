"""The live track record: every day's picks, saved permanently and scored against the S&P 500.

Unlike the backtest, nothing here can be tuned after the fact. Each morning's picks are appended
to data/live/picks.csv (committed to GitHub, so every row carries a date nobody can change).
A pick stays open until its holding period ends; then its final result is written into the file
and never changes again.
"""
import os

import pandas as pd

import config

LEDGER = os.path.join(config.CACHE_DIR, "live", "picks.csv")
COLUMNS = ["date", "months", "rank", "ticker", "price", "sp500", "probability",
           "exit_date", "exit_price", "exit_sp500"]


def load():
    if not os.path.exists(LEDGER):
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(LEDGER, dtype={"ticker": str})


def record(date, horizons, monthly, spy):
    """Add today's picks (once per trading day) and close any whose holding period has ended."""
    ledger = load()
    day = date.strftime("%Y-%m-%d")
    spy_now = float(spy.dropna().iloc[-1])
    prices = monthly.ffill().iloc[-1]
    new = [{"date": day, "months": h["months"], "rank": p["rank"], "ticker": p["ticker"], "price": p["price"],
            "sp500": round(spy_now, 2), "probability": p["probability"]}
           for h in horizons for p in h["picks"]
           if not ((ledger["date"] == day) & (ledger["months"] == h["months"])).any()]
    if new:
        ledger = pd.concat([ledger, pd.DataFrame(new)], ignore_index=True)

    due = ledger["exit_date"].isna() & (
        pd.to_datetime(ledger["date"]) + ledger["months"].astype(int).apply(lambda m: pd.DateOffset(months=m))
        <= date)
    for i in ledger.index[due]:
        ledger.loc[i, ["exit_date", "exit_price", "exit_sp500"]] = [
            day, round(float(prices.get(ledger.at[i, "ticker"], float("nan"))), 2), round(spy_now, 2)]

    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    ledger[COLUMNS].to_csv(LEDGER, index=False)
    print(f"Live record: {len(new)} new picks saved, {int(due.sum())} closed, {len(ledger)} in total")
    return ledger


def scoreboard(ledger, monthly, spy, horizons):
    """Summary per holding period and one row per pick date, for the website."""
    if ledger.empty:
        return {"started": None, "horizons": []}
    prices = monthly.ffill().iloc[-1]
    spy_now = float(spy.dropna().iloc[-1])
    df = ledger.copy()
    closed = df["exit_date"].notna()
    df["now"] = df["ticker"].map(prices).where(~closed, df["exit_price"])
    df["sp_now"] = df["exit_sp500"].where(closed, spy_now)
    df["ret"] = df["now"] / df["price"] - 1
    df["sp_ret"] = df["sp_now"] / df["sp500"] - 1
    df["beat"] = df["ret"] > df["sp_ret"]
    out = {"started": df["date"].min(), "horizons": []}
    for h in horizons:
        g = df[df["months"] == h["months"]]
        if g.empty:
            continue
        done, open_ = g[g["exit_date"].notna()], g[g["exit_date"].isna()]
        cohorts = g.groupby("date").agg(ret=("ret", "mean"), sp_ret=("sp_ret", "mean"),
                                        beat=("beat", "sum"), n=("ticker", "size"),
                                        closed=("exit_date", lambda s: s.notna().all()),
                                        tickers=("ticker", lambda s: " ".join(s.head(5))))
        out["horizons"].append({
            "months": h["months"], "label": h["label"],
            "picks": len(g), "closed": len(done), "open": len(open_),
            "closed_wins": int(done["beat"].sum()), "closed_losses": int((~done["beat"]).sum()),
            "open_beating": int(open_["beat"].sum()),
            "avg_ret": round(float(g["ret"].mean()), 4), "avg_sp_ret": round(float(g["sp_ret"].mean()), 4),
            "cohorts": [{"date": d, "ret": round(float(r.ret), 4), "sp_ret": round(float(r.sp_ret), 4),
                         "beat": int(r.beat), "n": int(r.n), "closed": bool(r.closed), "tickers": r.tickers}
                        for d, r in cohorts.sort_index(ascending=False).head(60).iterrows()],
            "first_picks": [{"ticker": r.ticker, "price": r.price, "now": round(float(r.now), 2),
                             "ret": round(float(r.ret), 4), "sp_ret": round(float(r.sp_ret), 4)}
                            for r in g[g["date"] == g["date"].min()].sort_values("rank").itertuples()],
            "latest_date": g["date"].max(),
        })
    return out
