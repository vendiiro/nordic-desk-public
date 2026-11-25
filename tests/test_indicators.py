import numpy as np
import pandas as pd
import pytest

from nordic_desk.analysis_config import LongTh
from nordic_desk.indicators import compute, pe_frame


def _frame(close, start="2020-01-01", high=None):
    c = pd.Series(np.asarray(close, dtype=float), index=pd.bdate_range(start, periods=len(close)))
    return pd.DataFrame({"open": c, "high": c if high is None else pd.Series(high, index=c.index, dtype=float), "low": c, "close": c})


def test_sma_and_trend_on_linear_series():
    out = compute(_frame(np.arange(1, 301)))
    assert out["sma50"].iloc[-1] == pytest.approx(275.5) and out["sma200"].iloc[-1] == pytest.approx(200.5)
    assert out["trend"].iloc[-1] == "up" and out["dist200"].iloc[-1] == pytest.approx(300 / 200.5 - 1)


def test_downtrend():
    assert compute(_frame(np.arange(300, 0, -1)))["trend"].iloc[-1] == "down"


def test_flat_series_no_crash():
    out = compute(_frame(np.full(300, 10.0)))
    assert np.isnan(out["rsi"].iloc[-1]) and np.isnan(out["pct_b"].iloc[-1])
    assert out["drawdown"].iloc[-1] == 0 and out["vol"].iloc[-1] == 0


def test_rsi_all_gains_is_100():
    assert compute(_frame(np.arange(1, 60)))["rsi"].iloc[-1] == 100


def test_rsi_wilder_known_value():
    # alternating +2 / -1, ending on a -1: steady-state Wilder averages after a loss are
    # gain 26/27 and loss 14/27, so RS = 13/7 and RSI = 100 - 100 / (20/7) = 65.0
    c = np.cumsum([100] + [2 if i % 2 == 0 else -1 for i in range(400)])
    assert compute(_frame(c))["rsi"].iloc[-1] == pytest.approx(65.0, abs=1e-6)


def test_bollinger_uses_population_std():
    c = np.array([10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18, 20, 19, 21, 22], dtype=float)
    out = compute(_frame(c))
    w = c[-20:]
    assert out["bb_mid"].iloc[-1] == pytest.approx(w.mean())
    assert out["bb_up"].iloc[-1] == pytest.approx(w.mean() + 2 * w.std(ddof=0))
    assert out["pct_b"].iloc[-1] == pytest.approx((22 - out["bb_lo"].iloc[-1]) / (out["bb_up"].iloc[-1] - out["bb_lo"].iloc[-1]))


def test_high52_uses_daily_high_not_close():
    c = np.full(300, 10.0)
    h = c + 1
    h[-10] = 50
    out = compute(_frame(c, high=h))
    assert out["high52"].iloc[-1] == 50 and out["dist52"].iloc[-1] == pytest.approx(10 / 50 - 1)


def test_high52_falls_back_to_close_without_highs():
    df = _frame(np.arange(1, 301))
    df[["open", "high", "low"]] = np.nan
    assert compute(df)["high52"].iloc[-1] == 300


def test_mom_skips_last_month_and_changes():
    c = np.arange(1, 801, dtype=float)
    out = compute(_frame(c))
    assert out["mom"].iloc[-1] == pytest.approx(c[-22] / c[-253] - 1)
    assert out["ret3y"].iloc[-1] == pytest.approx(c[-1] / c[-757] - 1)
    assert out["chg_1w"].iloc[-1] == pytest.approx(c[-1] / c[-6] - 1)


def test_drawdown_full_history():
    out = compute(_frame([10, 20, 15, 18]))
    assert out["drawdown"].tolist() == pytest.approx([0, 0, -0.25, -0.1])


def test_short_history_trend_none():
    out = compute(_frame(np.linspace(10, 20, 150)))
    assert out["trend"].iloc[-1] is None and np.isnan(out["sma200"].iloc[-1]) and np.isnan(out["mom"].iloc[-1])


TH = LongTh()


def _close(n, start="2023-01-02", v=100.0):
    return pd.Series(v, index=pd.bdate_range(start, periods=n), dtype=float)


def test_pe_point_in_time_no_lookahead():
    c = _close(700)
    eps = [(pd.Timestamp("2023-03-31"), 4.0), (pd.Timestamp("2024-03-30"), 5.0)]
    pe = pe_frame(c, eps, TH)["pe"]
    assert pe.loc["2024-03-29"] == 25 and pe.loc["2024-04-01"] == 20
    assert np.isnan(pe.loc["2023-03-30"])  # before any EPS was public


def test_pe_null_for_negative_eps():
    pe = pe_frame(_close(50), [(pd.Timestamp("2022-01-01"), -1.0)], TH)["pe"]
    assert pe.isna().all()


def test_pe_pct_uses_trailing_window_only():
    c = _close(600)
    eps = [(pd.Timestamp("2022-01-01"), 5.0)]
    early = pe_frame(c, eps, TH).loc["2023-06-30", "pe_pct"]
    c2 = c.copy()
    c2.iloc[-50:] = 1000.0  # later prices must not move an earlier day's percentile
    assert pe_frame(c2, eps, TH).loc["2023-06-30", "pe_pct"] == early


def test_pe_pct_median_and_count():
    c = pd.Series(np.arange(1, 11, dtype=float), index=pd.bdate_range("2024-01-01", periods=10))
    f = pe_frame(c, [(pd.Timestamp("2023-01-01"), 1.0)], TH)
    assert f["pe_pct"].iloc[-1] == 1.0 and f["pe_pct"].iloc[0] == 1.0
    assert f["pe_median"].iloc[-1] == 5.5 and f["pe_n"].iloc[-1] == 10
