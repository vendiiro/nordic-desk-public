import math

import numpy as np
import pandas as pd
import pytest

from nordic_desk.volsize import MIN_OBS, first_part, suggestion, usual_series, vol63


def test_first_part_clamps():
    assert first_part(0.2, 0.2) == 1.0 and first_part(0.4, 0.2) == 0.25 and first_part(0.1, 0.2) == 1.0
    assert first_part(0.21, 0.2) == 1.0  # (0.2/0.21)^2 = 0.91: inside the dead band, small bumps are noise
    assert first_part(0.3, 0.2) == pytest.approx((0.2 / 0.3) ** 2)
    assert first_part(0.0, 0.2) == 1.0 and first_part(float("nan"), 0.2) == 1.0 and first_part(0.3, float("nan")) == 1.0


def test_usual_point_in_time():
    rng = np.random.default_rng(3)
    v = pd.Series(rng.uniform(0.1, 0.3, 600))
    a = usual_series(v)
    b = usual_series(pd.concat([v, pd.Series(np.full(200, 2.0))], ignore_index=True))
    assert a.equals(b.iloc[:600]) and a.iloc[: MIN_OBS - 1].isna().all() and not math.isnan(a.iloc[MIN_OBS - 1])


def _close(n, vol=0.01, seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, vol, n))), index=pd.bdate_range("2018-01-01", periods=n))


def test_suggestion_short_history_none():
    assert suggestion(_close(200)) is None


def test_suggestion_jumpy_now():
    c = pd.concat([_close(700, 0.01), _close(80, 0.03, seed=2).pipe(lambda x: x / x.iloc[0])])
    c.index = pd.bdate_range("2018-01-01", periods=len(c))
    s = suggestion(c)
    assert s["current"] > s["usual"] and 0.25 <= s["first"] < 1


def test_flat_series_no_crash():
    s = suggestion(pd.Series(10.0, index=pd.bdate_range("2018-01-01", periods=500)))
    assert s is None or s["first"] == 1.0
    assert vol63(pd.Series(10.0, index=pd.bdate_range("2018-01-01", periods=100))).iloc[-1] == 0
