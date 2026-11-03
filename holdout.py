"""The one-time final test on the held-out years:  python holdout.py

Every choice in the model (the six measures, the simple score, top 20%) was made using 2016-2022.
This replays the locked model on picks made from config.HOLDOUT_FROM_YEAR on, which nothing was
ever tuned on, exactly the way the Backtest tab replays 2016-2022. The result is saved to
outputs/holdout.json and shown on the website. Run it once: if the model is changed because of
what this shows, these years stop being an honest test.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import config
import data
import fundamentals
from features import build_panel
from forecast import horizon_label, summarize, track_record

OUT = os.path.join(config.OUTPUT_DIR, "holdout.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--again", action="store_true", help="overwrite an earlier result (defeats the purpose)")
    args = ap.parse_args()
    if os.path.exists(OUT) and not args.again:
        sys.exit(f"{OUT} already exists: the held-out years have been used. See it on the site's Backtest tab.")

    monthly, spy, members = data.load_prices()
    fund = fundamentals.build(monthly)
    fund["size"] = fundamentals.company_size(monthly, fund)
    result = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "model": config.MODEL_TYPE, "from_year": config.HOLDOUT_FROM_YEAR,
              "data_through": monthly.index[-1].strftime("%Y-%m-%d"), "horizons": []}
    for h in config.PICK_HORIZONS:
        config.HORIZON_MONTHS = h
        panel, names = build_panel(monthly, members, fund)
        before, _ = track_record(monthly, spy, panel, names, h, size=fund["size"])
        after, calibration = track_record(monthly, spy, panel, names, h, holdout=True, size=fund["size"])
        b, a = summarize(before), summarize(after)
        result["horizons"].append({"months": h, "label": horizon_label(h), "backtest": b, "holdout": a,
                                   "periods": after, "calibration": calibration})
        print(f"\n{horizon_label(h)}")
        for name, s in [("2016-2022 backtest", b), (f"Held-out {config.HOLDOUT_FROM_YEAR}+", a)]:
            if s:
                print(f"  {name:<20} beat S&P 500 in {s['beat_sp500']:>2}/{s['periods']:<2}  "
                      f"picks {s['avg_picks']:+.1%}  S&P {s['avg_sp500']:+.1%}  edge {s['avg_picks'] - s['avg_sp500']:+.1%}  "
                      f"avg stock {s['avg_average_stock']:+.1%}  ({s['first']} to {s['last']})")
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("\nSaved", OUT)


if __name__ == "__main__":
    main()
