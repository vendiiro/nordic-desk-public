import numpy as np
import pandas as pd
import pytest

from nordic_desk.stocks import rebased, stock_stats

IDX = pd.bdate_range("2024-11-01", periods=300)
RISING = pd.Series(100 * 1.001 ** np.arange(300), index=IDX)


def test_returns_match_offsets():
    s = stock_stats(RISING, RISING)
    assert s["d1"] == pytest.approx(0.001, abs=1e-12)
    assert s["w1"] == pytest.approx(1.001 ** 5 - 1, abs=1e-12)
    assert s["m1"] == pytest.approx(1.001 ** 21 - 1, abs=1e-12)
    assert s["m3"] == pytest.approx(1.001 ** 63 - 1, abs=1e-12)
    assert s["m6"] == pytest.approx(1.001 ** 126 - 1, abs=1e-12)
    assert s["y1"] == pytest.approx(1.001 ** 252 - 1, abs=1e-12)


def test_beta_of_self_is_one():
    noisy = RISING * (1 + 0.01 * np.sin(np.arange(300)))
    assert stock_stats(noisy, noisy)["beta"] == pytest.approx(1.0)


def test_drawdown_zero_when_rising():
    assert stock_stats(RISING, RISING)["mdd"] == 0.0


def test_range_position():
    s = stock_stats(RISING, RISING)
    assert s["pos"] == 1.0 and s["hi"] == RISING.iloc[-1]
    assert s["lo"] == pytest.approx(RISING.iloc[-253])


def test_ytd_uses_last_close_of_previous_year():
    base = RISING[RISING.index < "2025-01-01"].iloc[-1]
    assert stock_stats(RISING, RISING)["ytd"] == pytest.approx(RISING.iloc[-1] / base - 1)


def test_drawdown_measured():
    s = RISING.copy()
    s.iloc[-50:] = s.iloc[-51] * 0.8
    assert stock_stats(s, RISING)["mdd"] == pytest.approx(-0.2)


def test_rebased_starts_at_100():
    r = rebased(RISING)
    assert len(r) == 253 and r[0] == 100.0
    assert r[-1] == pytest.approx(100 * 1.001 ** 252)
