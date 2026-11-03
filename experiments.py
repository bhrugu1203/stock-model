"""Test new signals against the current model, fairly:  python experiments.py

Each candidate is added to the current model and replayed walk-forward (forecast.track_record)
for every holding period in config.PICK_HORIZONS and every quarterly start month: 12 results
for 3 holding periods. A candidate only PASSES if it beats the current model in most of
those 12 and by a meaningful average margin. The held-out years are never touched.

  python experiments.py                                  # test every candidate one at a time
  python experiments.py --combo accruals,asset_growth    # test several together
  python experiments.py --combo accruals --industry      # ...ranked within each industry
  python experiments.py --simple                         # machine learning vs a plain average of the inputs
"""
import argparse
import os
import warnings

import pandas as pd

import config
import data
import fundamentals
from features import CANDIDATE_BUILDERS, FUNDAMENTAL_BUILDERS, build_panel
from forecast import horizon_label, track_record

MIN_CELLS = 9       # must beat the current model in at least 9 of the 12 holding-period x start-month results
MIN_GAIN = 0.002    # ...and add at least 0.2 percentage points per holding period on average
OUT = os.path.join(config.OUTPUT_DIR, "experiments.csv")


def cells(periods):
    """Average edge over the average stock and over the S&P 500, per start month."""
    df = pd.DataFrame(periods)
    df["month"] = df["start"].str[-2:].astype(int)
    df["vs_avg"] = df["picks"] - df["average_stock"]
    df["vs_sp500"] = df["picks"] - df["sp500"]
    return df.groupby("month")[["vs_avg", "vs_sp500"]].mean()


def evaluate(variants, monthly, spy, members, fund, groups):
    """variants: {label: (feature names, industry-relative?[, model type])}.
    Returns one row per variant x horizon x month."""
    rows = []
    every = {**FUNDAMENTAL_BUILDERS, **CANDIDATE_BUILDERS}
    for h in config.PICK_HORIZONS:
        config.HORIZON_MONTHS = h
        panels = {False: build_panel(monthly, members, fund, builders=every)[0]}
        if any(v[1] for v in variants.values()):
            panels[True] = build_panel(monthly, members, fund, builders=every, groups=groups)[0]
        for label, (names, industry, *model_type) in variants.items():
            default_type = config.MODEL_TYPE
            config.MODEL_TYPE = model_type[0] if model_type else default_type
            periods, _ = track_record(monthly, spy, panels[industry], names, h)
            config.MODEL_TYPE = default_type
            for month, r in cells(periods).iterrows():
                rows.append({"variant": label, "horizon": horizon_label(h), "month": month,
                             "vs_avg": r["vs_avg"], "vs_sp500": r["vs_sp500"]})
            print(f"  {horizon_label(h):<9} {label}", flush=True)
    return pd.DataFrame(rows)


def verdicts(results, baseline="Current model"):
    base = results[results["variant"] == baseline].set_index(["horizon", "month"])
    out = []
    for label, g in results.groupby("variant", sort=False):
        g = g.set_index(["horizon", "month"])
        gain = g["vs_avg"] - base["vs_avg"]
        wins = int((gain > 0).sum())
        passed = label != baseline and wins >= MIN_CELLS and gain.mean() >= MIN_GAIN
        out.append({"variant": label, "edge vs avg stock": g["vs_avg"].mean(), "edge vs S&P 500": g["vs_sp500"].mean(),
                    "gain vs current": gain.mean(), "better in": f"{wins}/{len(gain)}",
                    "result": "baseline" if label == baseline else ("PASS" if passed else "fail")})
    return pd.DataFrame(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--combo", help="comma-separated candidates to test together")
    ap.add_argument("--industry", action="store_true", help="rank the financials within each industry")
    ap.add_argument("--simple", action="store_true", help="compare with a plain average of the ranked inputs")
    args = ap.parse_args()
    warnings.filterwarnings("ignore")

    monthly, spy, members = data.load_prices()
    fund = fundamentals.build(monthly)
    groups = fundamentals.sectors(monthly.columns)
    base = list(FUNDAMENTAL_BUILDERS)

    variants = {"Current model": (base, False)}
    if args.simple:
        other = "simple" if config.MODEL_TYPE == "forest" else "forest"
        variants["Simple score" if other == "simple" else "Random forest"] = (base, False, other)
    elif args.combo or args.industry:
        extra = [c.strip() for c in (args.combo or "").split(",") if c.strip()]
        label = " + ".join(extra) if extra else "Current model"
        variants[label + (" (within industry)" if args.industry else "")] = (base + extra, args.industry)
    else:
        variants.update({f"+ {c}": (base + [c], False) for c in CANDIDATE_BUILDERS})
        variants["Ranked within industry"] = (base, True)

    print(f"Testing {len(variants) - 1} variant(s) on {config.FIRST_TEST_YEAR}-{config.HOLDOUT_FROM_YEAR - 1} "
          f"(held-out years untouched)...")
    results = evaluate(variants, monthly, spy, members, fund, groups)
    table = verdicts(results)
    pd.set_option("display.width", 140)
    fmt = {c: (lambda x: f"{x * 100:+.2f}%") for c in ["edge vs avg stock", "edge vs S&P 500", "gain vs current"]}
    print("\nAverage edge per holding period (all horizons and start months):")
    print(table.to_string(index=False, formatters=fmt))
    print(f"\nPASS = better than the current model in at least {MIN_CELLS} of 12 results "
          f"and by at least {MIN_GAIN:.1%} on average.")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    table.to_csv(OUT, index=False, mode="a" if os.path.exists(OUT) and args.combo else "w",
                 header=not (os.path.exists(OUT) and args.combo))
    results.to_csv(OUT.replace(".csv", "_detail.csv"), index=False)


if __name__ == "__main__":
    main()
