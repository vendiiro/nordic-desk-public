import math

import numpy as np
import pandas as pd
import pytest

from nordic_desk.risk import add_scenario, asset_view, portfolio_stats, sell_scenario

N = 252
A = np.tile([0.01, -0.01, 0.01, -0.01], N // 4)   # A and B: equal variance, zero sample covariance
B = np.tile([0.01, 0.01, -0.01, -0.01], N // 4)
SIGMA = float(np.std(A, ddof=1) * math.sqrt(252))


def panel(**rets):
    idx = pd.bdate_range("2025-01-01", periods=N + 1)
    return pd.DataFrame({k: 100 * np.concatenate([[1.0], np.cumprod(1 + np.asarray(v))]) for k, v in rets.items()}, index=idx)


def test_two_equal_uncorrelated_assets():
    s = portfolio_stats(panel(A=A, B=B, SPY=A), {"A": 1.0, "B": 1.0}, 0.0, set())
    assert s.vol == pytest.approx(SIGMA / math.sqrt(2))
    assert s.risk_share["A"] == pytest.approx(0.5)
    assert s.beta == pytest.approx(0.5)


def test_risk_shares_sum_to_one():
    rng = np.random.default_rng(1)
    c = rng.normal(0, 0.02, N)
    s = portfolio_stats(panel(A=A, B=B, C=c, SPY=A), {"A": 3.0, "B": 1.0, "C": 2.0}, 0.0, set())
    assert sum(s.risk_share.values()) == pytest.approx(1.0)


def test_cash_lowers_vol_and_counts_in_enb():
    p = panel(A=A, B=B, SPY=A)
    no_cash = portfolio_stats(p, {"A": 1.0, "B": 1.0}, 0.0, set())
    with_cash = portfolio_stats(p, {"A": 1.0, "B": 1.0}, 1.0, set())
    assert with_cash.enb == pytest.approx(3.0)
    assert with_cash.vol == pytest.approx(no_cash.vol * 2 / 3)
    assert with_cash.total == 3.0


def test_tech_share():
    s = portfolio_stats(panel(A=A, B=B, SPY=A), {"A": 3.0, "B": 1.0}, 0.0, {"A"})
    assert s.tech == pytest.approx(0.75)


def test_bad_day_correlation_uses_worst_fifth():
    rng = np.random.default_rng(2)
    a = rng.normal(0, 0.01, N)
    worst = a <= np.quantile(a, 0.2)
    c = np.where(worst, a, rng.normal(0, 0.01, N))       # equals the portfolio on its worst days only
    p = panel(A=a, C=c, SPY=a)
    base = portfolio_stats(p, {"A": 1.0}, 0.0, set())
    v = asset_view(p, "C", base)
    assert v["down"] == pytest.approx(1.0)
    assert v["corr"] < 0.9


def test_worst_fall_and_return():
    r = np.r_[np.full(126, 0.01), np.full(126, -0.01)]
    s = portfolio_stats(panel(A=r, SPY=r), {"A": 1.0}, 0.0, set())
    assert s.worst == pytest.approx(0.99 ** 126 - 1)
    assert s.ret == pytest.approx(1.01 ** 126 * 0.99 ** 126 - 1)


def test_add_negatively_correlated_lowers_vol():
    p = panel(A=A, C=-A, SPY=A)
    base = portfolio_stats(p, {"A": 1.0}, 0.0, set())
    s = add_scenario(p, {"A": 1.0}, 0.0, set(), "C", 0.5)
    assert s["vol"] < base.vol
    assert s["total"] == 1.5
    assert "own_risk" in s


def test_sell_spreads_pro_rata():
    rng = np.random.default_rng(3)
    p = panel(A=A, B=B, C=rng.normal(0, 0.01, N), SPY=A)
    s = sell_scenario(p, {"A": 2.0, "B": 1.0, "C": 1.0}, 0.0, set(), "A")
    assert s["total"] == 4.0
    assert s["weights"] == pytest.approx({"B": 0.5, "C": 0.5})
