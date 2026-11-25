import numpy as np
import pytest

from nordic_desk.forecast import bootstrap_range, calibrate, christoffersen, garch_t_sigma, regime_sigma, rolling_lines


def garch_series(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    omega, a, b = 0.000002, 0.08, 0.9
    var, out = omega / (1 - a - b), []
    for _ in range(n):
        x = np.sqrt(var) * rng.standard_t(6) / np.sqrt(6 / 4)
        out.append(x)
        var = omega + a * x * x + b * var
    return np.array(out)


def test_garch_level():
    r = garch_series()
    s, params = garch_t_sigma(r)
    assert 0.003 < s < 0.04 and params["nu"] > 2


def test_regime_finds_the_volatile_stretch():
    rng = np.random.default_rng(1)
    r = np.concatenate([rng.normal(0, 0.006, 1500), rng.normal(0, 0.03, 120)])
    s, p_high, lo, hi = regime_sigma(r)
    assert p_high > 0.8 and hi > 3 * lo and s > 0.02


def test_bootstrap_brackets_and_scales():
    rng = np.random.default_rng(2)
    r = rng.normal(0, 0.01, 1500)
    lo, hi = bootstrap_range(r, horizon=21)
    lo2, hi2 = bootstrap_range(2 * r, horizon=21)
    assert lo < 0 < hi and hi2 == pytest.approx(2 * hi, rel=0.25)


@pytest.mark.parametrize("model", ["ewma", "garch", "bootstrap", "regime"])
def test_rolling_lines_no_look_ahead(model):
    r = garch_series(700, seed=3)
    a = rolling_lines(r, model, min_train=504)
    r2 = r.copy()
    r2[-1] = -0.5
    b = rolling_lines(r2, model, min_train=504)
    assert len(a) == 700 - 504 and np.allclose(a[:-1], b[:-1]) and (a < 0).all()


def test_christoffersen_flags_clusters():
    spread = np.random.default_rng(7).random(1000) < 0.05   # independent breaches
    clustered = np.zeros(1000, bool)
    clustered[500:550] = True
    assert christoffersen(spread) > 0.05 and christoffersen(clustered) < 0.001


def test_calibrate_reports_every_model():
    out = calibrate(garch_series(800, seed=4), min_train=504)
    assert set(out) == {"ewma", "garch", "bootstrap", "regime"}
    assert {"n", "hits", "rate", "kupiec_p", "christoffersen_p"} <= set(out["garch"])
