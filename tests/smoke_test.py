"""Quick check that the pipeline runs end to end on fake data:  python tests/smoke_test.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import data
from backtest import run_backtest, scorecard
from features import build_panel

monthly, spy, members = data.synthetic_prices()
panel, names = build_panel(monthly, members)
res, model = run_backtest(monthly, spy, panel, names)
assert len(res) >= 8 and model is not None
assert not res.isna().any().any()
print(scorecard(res)[1])
print("SMOKE TEST PASSED")
