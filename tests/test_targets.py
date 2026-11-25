import numpy as np
import pandas as pd
import pytest

from nordic_desk.targets import MIN_OWN, STUDY, check, monthly_snapshots, per_ticker, rates, realistic


def row(date, ticker="AAA", price=100.0, target=120.0):
    return {"date": date, "ticker": ticker, "price": str(price), "target_mean": str(target)}


def test_monthly_dedupe():
    rows = [row("2025-01-07"), row("2025-01-03"), row("2025-02-10"), row("2025-01-05", "BBB")]
    out = monthly_snapshots(rows)
    assert [(r["ticker"], r["date"]) for r in out] == [("AAA", "2025-01-03"), ("BBB", "2025-01-05"), ("AAA", "2025-02-10")]


def test_check_met_flags():
    idx = pd.bdate_range("2025-01-01", periods=300)
    c = np.full(300, 100.0)
    c[60:80] = 125.0  # crosses the 120 target in month 3, then falls back
    close = pd.Series(c, index=idx)
    out = check([row("2025-01-01")], lambda t: close)
    r = out[0]
    assert r["met_any"] is True and r["met_12m"] is False
    assert r["implied"] == pytest.approx(0.2) and r["actual"] == pytest.approx(0.0)


def test_check_skips_too_recent():
    close = pd.Series(100.0, index=pd.bdate_range("2025-01-01", periods=100))
    assert check([row("2025-01-01")], lambda t: close) == []


def test_rates_use_study_until_30():
    checked = [{"ticker": "A", "date": "2024-01-01", "met_12m": True, "met_any": True, "implied": 0.2, "actual": 0.2}] * (MIN_OWN - 1)
    r = rates(checked, "2024-01-01")
    assert r["overshoot"] == STUDY["overshoot"] and r["source"] == STUDY["source"] and r["n_checked"] == MIN_OWN - 1
    assert r["first_check"] == "2024-12-31"


def test_rates_switch_to_own_record():
    checked = [{"ticker": "A", "date": "2024-01-01", "met_12m": i % 2 == 0, "met_any": True, "implied": 0.3, "actual": 0.1}
               for i in range(MIN_OWN)]
    r = rates(checked, "2024-01-01")
    assert r["overshoot"] == pytest.approx(0.2) and r["met_12m"] == 0.5 and r["met_any"] == 1.0
    assert r["source"] == f"own record ({MIN_OWN})"


def test_realistic_subtracts_overshoot():
    assert realistic(0.21, 0.15) == pytest.approx(0.06) and realistic(None, 0.15) is None


def test_missing_history_file():
    r = rates([], None)
    assert r["n_checked"] == 0 and r["first_check"] is None and r["met_12m"] == STUDY["met_12m"]
    assert per_ticker([]) == {}


def test_check_is_split_safe():
    idx = pd.bdate_range("2025-01-01", periods=300)
    close = pd.Series(np.full(300, 50.0), index=idx)  # history rescaled after a 2:1 split: snapshot price 100 shows as 50
    r = check([row("2025-01-01", price=100.0, target=110.0)], lambda t: close)[0]
    assert r["actual"] == pytest.approx(0.0) and r["met_12m"] is False and r["implied"] == pytest.approx(0.1)
    c2 = close.copy()
    c2.iloc[150:] = 25.0  # an unadjusted split step inside the window: skip, don't score
    assert check([row("2025-01-01", price=50.0, target=55.0)], lambda t: c2) == []
