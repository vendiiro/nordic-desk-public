import numpy as np
import pandas as pd
import pytest

from nordic_desk.lumpspread import lump_vs_spread, outcomes


def series(values, start="2020-01-01"):
    return pd.Series(np.asarray(values, float), index=pd.bdate_range(start, periods=len(values)))


def test_rising_line_lump_always_ahead():
    r = lump_vs_spread(series(np.linspace(100, 300, 800)), 6)
    assert r["lump_ahead"] == 1.0 and r["median_diff"] > 0 and r["starts"] > 0
    assert sum(r["hist"]["counts"]) == r["starts"] and len(r["hist"]["edges"]) == 21


def test_flat_series_equal():
    r = lump_vs_spread(series(np.full(600, 10.0)), 3)
    assert r["lump_ahead"] == 0.0 and r["median_diff"] == 0 and r["lump_median"] == pytest.approx(1.0)
    assert r["worst_lump_regret"] == 0 and r["worst_spread_regret"] == 0


def test_known_two_step_value():
    idx = pd.bdate_range("2020-01-01", periods=400)
    close = pd.Series(np.where(idx < pd.Timestamp("2020-02-01"), 1.0, 2.0), index=idx)
    o = outcomes(close, 3, 252)
    first = o.iloc[0]
    assert first["start"] == idx[0] and first["L"] == pytest.approx(2.0) and first["S"] == pytest.approx(4 / 3)
    assert o.iloc[1]["L"] == pytest.approx(1.0) and o.iloc[1]["S"] == pytest.approx(1.0)


def test_k12_values_last_tranche_at_same_end_date():
    close = series(np.linspace(100, 200, 700))
    o = outcomes(close, 12, 252)
    s0 = o.iloc[0]
    j_end = 252
    assert s0["L"] == pytest.approx(close.iloc[j_end] / close.iloc[0])
    assert s0["S"] < s0["L"]  # the later tranches bought higher on a rising line


def test_short_history_none():
    assert lump_vs_spread(series(np.full(200, 1.0)), 6) is None


from nordic_desk.lumpspread import vs_outcomes, vs_value, volsized


def test_vs_value_arithmetic():
    p = np.array([1.0, 2.0, 2.0, 2.0, 2.0])
    # f = 0.25 at index 0 (price 1), rest 0.75 in 3 parts at indexes 1, 2, 3 (price 2), all valued at index 4 (price 2)
    assert vs_value(p, 0, [1, 2, 3], 4, 0.25) == pytest.approx(0.25 * 2 + 0.75 / 3 * 3)
    assert vs_value(p, 0, [1, 2, 3], 4, 1.0) == pytest.approx(2.0)  # f = 1 is the lump


def _calm(n=900):
    r = np.where(np.arange(n) % 2 == 0, 0.01, -0.009)  # identical volatility every window
    return pd.Series(100 * np.exp(np.cumsum(r)), index=pd.bdate_range("2016-01-01", periods=n))


def test_volsized_equals_lump_when_calm():
    r = volsized(_calm(), 6)
    assert r["starts"] > 0 and r["held_back"] == 0 and r["beat_lump"] is None and r["median"] is None


def test_volsized_point_in_time_and_triggers():
    rng = np.random.default_rng(5)
    r1 = np.concatenate([rng.normal(0, 0.01, 700), rng.normal(0, 0.04, 200), rng.normal(0, 0.01, 400)])
    c = pd.Series(100 * np.exp(np.cumsum(r1)), index=pd.bdate_range("2016-01-01", periods=len(r1)))
    a = vs_outcomes(c.iloc[:1000], 6)
    b = vs_outcomes(c, 6)
    assert a.equals(b.iloc[:len(a)])
    r = volsized(c, 6)
    assert r["held_back"] > 0 and 0 <= r["beat_lump"] <= 1 and (b["f"] < 1).any() and b["f"].min() >= 0.25


def test_volsized_short_history_none():
    assert volsized(series(np.full(300, 1.0)), 6) is None
