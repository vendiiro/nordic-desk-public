import math

import numpy as np
import pandas as pd
import pytest

from nordic_desk.analysis_config import EntryTh
from nordic_desk.scorecard import group_stats, month_starts, nw_interval, samples, stock_reading, verdict_series


def ohlc(close, start="2018-01-01"):
    c = pd.Series(np.asarray(close, float), index=pd.bdate_range(start, periods=len(close)))
    return pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c})


def test_nw_lag0_equals_plain_se():
    m, lo, hi = nw_interval(np.array([1, 2, 3, 4, 5.0]), 0)
    se = math.sqrt(2) / math.sqrt(5)
    assert m == 3 and lo == pytest.approx(3 - 1.96 * se) and hi == pytest.approx(3 + 1.96 * se)


def test_nw_wider_with_positive_autocorrelation():
    rng = np.random.default_rng(1)
    x = np.zeros(200)
    for i in range(1, 200):
        x[i] = 0.8 * x[i - 1] + rng.normal()
    _, lo0, hi0 = nw_interval(x, 0)
    _, lo5, hi5 = nw_interval(x, 5)
    assert hi5 - lo5 > hi0 - lo0


def test_nw_constant_and_tiny_series():
    assert nw_interval(np.full(10, 0.02), 3) == pytest.approx((0.02, 0.02, 0.02))
    m, lo, hi = nw_interval(np.array([0.5]), 0)
    assert m == 0.5 and math.isnan(lo) and math.isnan(hi)


def test_month_starts_skips_missing_months_and_uses_first_available():
    idx = pd.DatetimeIndex(["2026-01-05", "2026-01-06", "2026-03-03", "2026-03-04"])
    assert list(month_starts(idx)) == [pd.Timestamp("2026-01-05"), pd.Timestamp("2026-03-03")]


def test_samples_horizon_and_dropped_tail():
    idx = pd.bdate_range("2024-01-01", periods=300)
    stock = pd.Series(np.linspace(100, 130, 300), index=idx)
    spy = pd.Series(50.0, index=idx)
    groups = pd.Series("steady", index=idx, dtype=object)
    out = samples(groups, stock, spy, 21)
    first = out.iloc[0]
    assert first["date"] == idx[0] and first["excess"] == pytest.approx(stock.iloc[21] / stock.iloc[0] - 1)
    assert bool(first["beat"]) and out["date"].max() <= idx[-22]


def test_samples_skip_none_groups_and_spy_holiday():
    idx = pd.bdate_range("2024-01-01", periods=100)
    stock = pd.Series(100.0, index=idx)
    spy = pd.Series(100.0, index=idx).drop(idx[21])  # SPY closed on the end day: use its previous close
    groups = pd.Series([None] * 100, index=idx, dtype=object)
    groups.iloc[0] = "pullback"
    out = samples(groups, stock, spy, 21)
    assert len(out) == 1 and out.iloc[0]["excess"] == 0 and out.iloc[0]["group"] == "pullback"


def test_verdicts_point_in_time():
    rng = np.random.default_rng(4)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, 600)))
    a = verdict_series(ohlc(c[:500]), EntryTh())
    b = verdict_series(ohlc(c), EntryTh())
    assert a.equals(b.iloc[:500])
    assert set(b.dropna()) <= {"pullback", "steady", "stretched", "wait_down", "wait_mixed"}


def _s(n_months, value, group="steady"):
    months = pd.period_range("2015-01", periods=n_months, freq="M")
    return pd.DataFrame({"date": months.to_timestamp(), "month": months, "group": group, "excess": value, "beat": value > 0})


def test_group_stats_too_few_and_helps():
    st = group_stats(_s(60, 0.02), 21, good=True)
    assert st["reading"] == "helps" and st["n_months"] == 60 and st["beat"] == 1.0
    assert group_stats(_s(60, 0.02), 126, good=True)["reading"] == "too few"  # 60 / 6 = 10 windows
    assert group_stats(_s(60, -0.02, "wait_down"), 21, good=False)["reading"] == "helps"
    assert group_stats(_s(60, -0.02), 21, good=True)["reading"] == "works against"


def test_stock_reading_never_says_helps():
    helps = {"reading": "helps", "lo": 0.01, "hi": 0.03, "eff_windows": 20}
    noisy = {"reading": "no clear edge", "lo": -0.01, "hi": 0.03, "eff_windows": 20}
    assert stock_reading(helps, "helps", good=True) == "consistent with the pooled reading"
    assert stock_reading(helps, "no clear edge", good=True) == "too noisy to trust alone"
    assert stock_reading(noisy, "helps", good=True) == "too noisy to trust alone"
    assert stock_reading({**helps, "eff_windows": 5}, "helps", good=True) == "too noisy to trust alone"


def test_samples_skip_months_before_the_price_series_starts():
    idx = pd.bdate_range("2024-01-01", periods=300)
    groups = pd.Series("steady", index=idx, dtype=object)
    stock = pd.Series(np.linspace(100, 130, 200), index=idx[100:])  # prices start in late May
    out = samples(groups, stock, pd.Series(50.0, index=idx), 21)
    assert out["date"].min().to_period("M") == idx[100].to_period("M") and out["date"].is_unique
    assert len(out) == len(out["excess"].drop_duplicates())
