import math

import numpy as np
import pandas as pd
import pytest

from nordic_desk.forecast import ewma_sigma, portfolio_forecast, var_backtest
from nordic_desk.panel import eur_panel


def test_ewma_constant_returns_vol():
    r = np.tile([0.01, -0.01], 300)
    s = ewma_sigma(r)
    assert s[-1] == pytest.approx(0.01, rel=1e-3)
    assert len(s) == len(r) + 1          # last value forecasts the next day


def test_backtest_counts_hits_and_kupiec():
    rng = np.random.default_rng(1)
    r = rng.normal(0, 0.01, 4000)
    bt = var_backtest(r, np.full(len(r), 0.01))
    assert bt["n"] == 4000 and 0.03 < bt["rate"] < 0.07 and bt["p_value"] > 0.01
    bad = var_backtest(r, np.full(len(r), 0.004))   # sigma too small: far too many breaches
    assert bad["rate"] > 0.2 and bad["p_value"] < 1e-6


def _panel(n=800):
    idx = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.default_rng(2)
    return pd.DataFrame({"A": 100 * np.cumprod(1 + rng.normal(0, 0.01, n)),
                         "ETH-EUR": 100 * np.cumprod(1 + rng.normal(0, 0.05, n))}, index=idx)


def test_portfolio_forecast_models_and_headline(tmp_path):
    f = portfolio_forecast(_panel(), {"A": 1000.0, "ETH-EUR": 100.0}, cash=0.0, horizon=21, cache_path=tmp_path / "c.json")
    assert set(f["models"]) == {"ewma", "garch", "bootstrap", "regime"} and f["headline"] in f["models"]
    assert f["excluded"] == ["ETH-EUR"] and f["value"] == 1100.0
    for m in f["models"].values():
        assert m["low"] < 1100 < m["high"] and m["calibration"]["n"] == 799 - 504
    h = f["models"][f["headline"]]
    assert f["low"] == h["low"] and f["vol_ann"] == pytest.approx(f["sigma_daily"] * math.sqrt(252))
    assert 0 <= f["regime"]["p_high"] <= 1


def test_calibration_cached(tmp_path, monkeypatch):
    import nordic_desk.forecast as fc
    calls = []
    real = fc.calibrate
    monkeypatch.setattr(fc, "calibrate", lambda r, **k: calls.append(1) or real(r, **k))
    for _ in range(2):
        fc.portfolio_forecast(_panel(), {"A": 1000.0}, 0.0, cache_path=tmp_path / "c.json", today="2026-01-14")
    assert len(calls) == 1


def test_panel_all_history():
    a = pd.Series(np.arange(1, 501, dtype=float), index=pd.bdate_range("2020-01-01", periods=500))
    b = a.iloc[200:]
    fx = pd.Series(1.0, index=a.index)
    p = eur_panel({"A": a, "B": b}, {"A": "EUR", "B": "EUR"}, fx, end="2030-01-01", n_returns=None)
    assert len(p) == 300 and not p.isna().any().any()


def test_short_history_has_no_calibration(tmp_path):
    f = portfolio_forecast(_panel(300), {"A": 1000.0}, 0.0, cache_path=tmp_path / "c.json")
    assert f["headline"] == "ewma" and f["backtest"] is None
    assert all(m["calibration"] is None for m in f["models"].values())


def test_bootstrap_range_uses_the_calibrated_window():
    from nordic_desk.forecast import HS_WINDOW, bootstrap_range
    rng = np.random.default_rng(5)
    r = rng.normal(0, 0.01, 1500)
    r2 = r.copy()
    r2[: len(r) - HS_WINDOW] *= 10            # change only days outside the window
    assert bootstrap_range(r[-HS_WINDOW:]) == bootstrap_range(r2[-HS_WINDOW:])
    f1 = portfolio_forecast(_panel(800), {"A": 1000.0}, 0.0, cache_path=None, today="2026-01-14")
    assert f1["models"]["bootstrap"]["label"] == "Bootstrap, last 500 days"


def test_cache_survives_small_weight_moves(tmp_path, monkeypatch):
    import nordic_desk.forecast as fc
    calls = []
    real = fc.calibrate
    monkeypatch.setattr(fc, "calibrate", lambda r, **k: calls.append(1) or real(r, **k))
    p = _panel(800)
    p2 = p.copy()
    p2.iloc[-1, 0] *= 1.001                    # a price move changes today's weights a little
    fc.portfolio_forecast(p, {"A": 1000.0}, 50.0, cache_path=tmp_path / "c.json", today="2026-01-14")
    fc.portfolio_forecast(p2, {"A": 1001.0}, 50.0, cache_path=tmp_path / "c.json", today="2026-01-15")
    assert len(calls) == 1


def test_failed_model_is_dropped(tmp_path, monkeypatch):
    import nordic_desk.forecast as fc
    monkeypatch.setattr(fc, "garch_t_sigma", lambda r: (_ for _ in ()).throw(RuntimeError("no fit")))
    f = fc.portfolio_forecast(_panel(300), {"A": 1000.0}, 0.0, cache_path=tmp_path / "c.json")
    assert "garch" not in f["models"] and "garch" in f["failed"]


def test_all_excluded_gives_no_forecast(tmp_path):
    assert portfolio_forecast(_panel(300), {"ETH-EUR": 100.0}, 0.0, cache_path=tmp_path / "c.json") is None
