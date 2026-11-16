"""Check that a partial or stale price download is refused:  python tests/download_guard_test.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import data
from forecast import download_problem

monthly, spy, members = data.synthetic_prices()
members.iloc[-1] = True   # everyone is a member today
assert download_problem(monthly, spy, members) is None

partial = monthly.copy()
partial.iloc[-1, : len(partial.columns) // 4] = np.nan   # a quarter of stocks missing today's price
assert "have a price" in download_problem(partial, spy, members)

few = monthly.copy()
few.iloc[-1, :3] = np.nan                                # a handful missing is normal
assert download_problem(few, spy, members) is None

no_spy = spy.copy()
no_spy.iloc[-1] = np.nan
assert "SPY" in download_problem(monthly, no_spy, members)

later = {"data_through": "2030-01-01"}
assert "older than the last picks" in download_problem(monthly, spy, members, later)
assert download_problem(monthly, spy, members, {"data_through": "2030-01-01", "demo": True}) is None
print("DOWNLOAD GUARD TEST PASSED")
