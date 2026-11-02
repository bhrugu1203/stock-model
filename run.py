"""Run the whole pipeline:  python run.py   (see README.md for options)"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config
import data
import fundamentals
from backtest import run_backtest, scorecard
from features import build_panel
from picks import current_picks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="use fake data (offline test, results meaningless)")
    ap.add_argument("--refresh", action="store_true", help="re-download prices instead of using the cache")
    ap.add_argument("--no-fundamentals", action="store_true", help="skip the slow P/E lookups for picks")
    ap.add_argument("--final", action="store_true",
                    help=f"also score the held-out years ({config.HOLDOUT_FROM_YEAR}+). Do this rarely: "
                         "once you tune on these years they stop being an honest test")
    args = ap.parse_args()

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    monthly, spy, members = data.synthetic_prices() if args.demo else data.load_prices(refresh=args.refresh)
    print(f"{monthly.shape[1]} stocks, {len(monthly)} months of data")
    if not args.demo and config.UNIVERSE == "historical":
        cov = data.coverage(monthly, members, data.get_sp500_history())
        cov = cov[cov.index.year >= config.FIRST_TEST_YEAR]
        print(f"Price coverage of real index members: {cov.min():.0%} to {cov.max():.0%} "
              "(the rest have no Yahoo data, mostly companies that were bought out, went bust or renamed)")

    fund = None
    if config.USE_FUNDAMENTALS:
        fund = fundamentals.synthetic(monthly) if args.demo else fundamentals.build(monthly, refresh=args.refresh)
    panel, names = build_panel(monthly, members, fund)
    res, model = run_backtest(monthly, spy, panel, names, final=args.final)
    if not args.final:
        print(f"\n(Years {config.HOLDOUT_FROM_YEAR}+ are held out for a final check: python run.py --final)")

    print("\nYearly returns % (buy in rebalance month, hold one horizon):")
    print((res * 100).round(1).to_string())
    growth, card = scorecard(res)
    print("\nScorecard:")
    print(card.to_string())

    growth.plot(figsize=(9, 5), title="Growth of $1 (walk-forward backtest)")
    plt.grid(alpha=0.3)
    plt.savefig(os.path.join(config.OUTPUT_DIR, "growth.png"), dpi=120, bbox_inches="tight")
    res.to_csv(os.path.join(config.OUTPUT_DIR, "yearly_returns.csv"))

    if model is not None:
        imp = pd.Series(model.feature_importances_, index=names).sort_values()
        print("\nFeature importance:")
        print(imp.round(3).to_string())

    latest, picks = current_picks(monthly, panel, names, with_fundamentals=not (args.demo or args.no_fundamentals))
    print(f"\nTop picks as of {latest.date()}:")
    print(picks.round(3).to_string())
    picks.to_csv(os.path.join(config.OUTPUT_DIR, "current_picks.csv"))
    print("\nSaved charts and CSVs to", config.OUTPUT_DIR + "/")
    print("Reminder: educational project, not financial advice. See README limitations.")


if __name__ == "__main__":
    main()
