import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from nordic_desk.goalrange import Goals, backtest_1y, load_goals, portfolio_returns, recentre, simulate


def _write(tmp_path, text):
    p = tmp_path / "goals.local.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_goals_missing_file_gives_defaults(tmp_path):
    g = load_goals(tmp_path / "nope.toml")
    assert g == Goals() and g.monthly_eur == 0 and g.target_eur is None and g.years == 5 and not g.from_file


def test_load_goals_reads_and_validates(tmp_path):
    g = load_goals(_write(tmp_path, "target_eur = 50000\ntarget_year = 2031\nmonthly_eur = 300\nlump_eur = 1000\n"
                                    "max_drawdown = 0.3\nyears = 7\n"))
    assert (g.target_eur, g.target_year, g.monthly_eur, g.lump_eur, g.max_drawdown, g.years) == (50000, 2031, 300, 1000, 0.3, 7)
    assert g.from_file
    with pytest.raises(ValueError, match="years"):
        load_goals(_write(tmp_path, "years = 11\n"))
    with pytest.raises(ValueError, match="target_year"):
        load_goals(_write(tmp_path, "target_eur = 50000\n"))
    with pytest.raises(ValueError, match="monthly_eur"):
        load_goals(_write(tmp_path, "monthly_eur = -5\n"))
    with pytest.raises(ValueError, match="unknown"):
        load_goals(_write(tmp_path, "monthy_eur = 5\n"))


def test_example_goals_file_loads():
    g = load_goals("config/goals.example.toml")
    assert g.from_file and 1 <= g.years <= 10


def test_portfolio_returns_counts_excluded_as_cash():
    idx = pd.bdate_range("2020-01-01", periods=4)
    panel = pd.DataFrame({"A": [100.0, 110, 121, 121], "ETH-EUR": [10.0, 20, 5, 50]}, index=idx)
    rp, w, total, excluded = portfolio_returns(panel, {"A": 500.0, "ETH-EUR": 250.0}, cash=250.0)
    assert total == 1000.0 and excluded == ["ETH-EUR"] and w == {"A": 0.5}
    assert np.allclose(rp, [0.05, 0.05, 0.0])


def test_portfolio_returns_none_when_nothing_modelled():
    idx = pd.bdate_range("2020-01-01", periods=4)
    panel = pd.DataFrame({"ETH-EUR": [10.0, 20, 5, 50]}, index=idx)
    assert portfolio_returns(panel, {"ETH-EUR": 250.0}, cash=0.0) is None


def test_recentre_sets_the_mean_and_keeps_the_spread():
    rng = np.random.default_rng(0)
    lr = rng.normal(0.001, 0.01, 2000)
    out = recentre(lr, 0.07)
    assert out.mean() == pytest.approx(math.log(1.07) / 252)
    assert out.std() == pytest.approx(lr.std())


def _const(n=1000, daily=None):
    return np.full(n, daily if daily is not None else 1.07 ** (1 / 252) - 1)


def test_simulate_constant_returns_compound_exactly():
    # zero volatility: every path is the drift path, so every percentile equals the compound value
    g = Goals(monthly_eur=0, years=3)
    r = simulate(_const(), 1000.0, g, drift=0.07, n=200, today=date(2026, 11, 24))
    assert [y["year"] for y in r["years"]] == [1, 2, 3]
    for y in r["years"]:
        for k in ("p5", "p25", "p50", "p75", "p95"):
            assert y[k] == pytest.approx(1000 * 1.07 ** y["year"], rel=1e-9)
    assert r["years"][0]["date"] == "2027-11-24"
    assert r["years"][2]["growth"]["0.5"] == pytest.approx(1.07 ** 3 - 1)  # returns without new money, for the ledger
    assert r["contributions"] == [1000.0, 1000.0, 1000.0]
    assert r["drawdown"]["p95"] == pytest.approx(0.0, abs=1e-12) and r["goal"] is None


def test_simulate_monthly_contributions_on_a_flat_path():
    g = Goals(monthly_eur=100, lump_eur=500, years=2)
    r = simulate(np.zeros(800), 1000.0, g, drift=0.0, n=50, today=date(2026, 1, 2))
    assert r["years"][0]["p50"] == pytest.approx(1500 + 12 * 100)
    assert r["years"][1]["p50"] == pytest.approx(1500 + 24 * 100)
    assert r["contributions"] == [2700.0, 3900.0]


def test_monthly_needed_reproduces_the_target():
    g = Goals(target_eur=5000.0, target_year=2028, monthly_eur=50, years=2)
    r = simulate(_const(), 1000.0, g, drift=0.07, n=100, today=date(2026, 6, 1))
    m = r["goal"]["monthly_50"]
    growth = [(1.07 ** (1 / 12)) ** (24 - k) for k in range(24)]
    assert 1000 * 1.07 ** 2 + m * sum(growth) == pytest.approx(5000, rel=1e-9)
    assert r["goal"]["monthly_75"] == pytest.approx(m)
    assert r["goal"]["prob"] == 0.0 and r["goal"]["year"] == 2028 and r["goal"]["years_ahead"] == 2


def test_goal_already_met_needs_no_saving():
    g = Goals(target_eur=500.0, target_year=2027, years=1)
    r = simulate(_const(), 1000.0, g, drift=0.07, n=50, today=date(2026, 6, 1))
    assert r["goal"]["monthly_50"] == 0.0 and r["goal"]["prob"] == 1.0


def test_goal_outside_horizon_is_explained_not_simulated():
    past = simulate(_const(), 1000.0, Goals(target_eur=5000.0, target_year=2026, years=3), 0.07, n=20, today=date(2026, 6, 1))
    far = simulate(_const(), 1000.0, Goals(target_eur=5000.0, target_year=2040, years=3), 0.07, n=20, today=date(2026, 6, 1))
    assert past["goal"]["prob"] is None and "next year" in past["goal"]["note"]
    assert far["goal"]["prob"] is None and "10 years" in far["goal"]["note"]


def test_horizon_extends_to_the_target_year():
    r = simulate(_const(), 1000.0, Goals(target_eur=5000.0, target_year=2033, years=3), 0.07, n=20, today=date(2026, 6, 1))
    assert len(r["years"]) == 7


def test_sensitivity_and_drawdown_on_noisy_returns():
    rng = np.random.default_rng(3)
    rp = rng.normal(0.0003, 0.012, 2500)
    g = Goals(target_eur=1600.0, target_year=2031, monthly_eur=0, max_drawdown=0.2, years=5)
    a = simulate(rp, 1000.0, g, drift=0.07, n=2000, seed=1, today=date(2026, 6, 1))
    b = simulate(rp, 1000.0, g, drift=0.07, n=2000, seed=1, today=date(2026, 6, 1))
    assert a == b
    q = a["goal"]
    assert q["prob_low"] < q["prob"] < q["prob_high"]
    y5 = a["years"][4]
    assert y5["p5"] < y5["p25"] < y5["p50"] < y5["p75"] < y5["p95"]
    assert y5["p50"] == pytest.approx(1000 * 1.07 ** 5, rel=0.08)  # re-centred: the median sits near the stated drift
    d = a["drawdown"]
    assert d["limit"] == 0.2 and 0 < d["p50"] < d["p95"] < 1 and 0 < d["prob_exceed"] < 1
    assert a["drift"] == 0.07 and a["n_paths"] == 2000


def test_drawdown_ignores_new_money():
    # a 20% fall then flat; big monthly savings must not hide it
    rp = np.zeros(600)
    rp[0] = -0.2
    r = simulate(rp, 1000.0, Goals(monthly_eur=10_000, years=1), drift=0.0, n=30, block=600, today=date(2026, 1, 2))
    assert r["drawdown"]["p95"] > 0


def test_backtest_needs_four_years():
    assert backtest_1y(np.zeros(900), 0.07) is None


def test_backtest_has_no_look_ahead():
    rng = np.random.default_rng(5)
    rp = rng.normal(0.0003, 0.01, 1500)
    a = backtest_1y(rp, 0.07, n=300)
    changed = rp.copy()
    changed[-100:] = 0.05  # only the last days change: checks whose pool and year end before them stay the same
    b = backtest_1y(changed, 0.07, n=300)
    early_a = [c for c in a["checks"] if c["day"] + 252 <= 1400]
    early_b = [c for c in b["checks"] if c["day"] + 252 <= 1400]
    assert early_a == early_b and len(early_a) > 0


def test_backtest_covers_near_nominal_on_iid_returns():
    rng = np.random.default_rng(7)
    lr = rng.normal(math.log(1.07) / 252, 0.01, 6000)
    bt = backtest_1y(np.expm1(lr), 0.07, n=1000)
    assert bt["n"] == len(bt["checks"]) > 200
    assert 0.8 < bt["inside_90"] < 0.97 and 0.38 < bt["inside_50"] < 0.62
    assert bt["n_independent"] == bt["n"] // 12
    assert 0 <= bt["p_90"] <= 1 and 0 <= bt["p_50"] <= 1


def test_cash_earns_nothing_so_the_drift_applies_to_the_invested_part():
    # half the portfolio in cash at zero volatility: the paths grow about 3.5% a year, not 7%
    r = simulate(np.zeros(800), 1000.0, Goals(years=1), drift=0.07, n=20, invested=0.5, today=date(2026, 1, 2))
    assert r["years"][0]["p50"] == pytest.approx(1000 * 1.035, rel=1e-9)
    assert r["drift"] == 0.07 and r["invested"] == 0.5
    bt = backtest_1y(np.zeros(1200), 0.07, invested=0.5, n=50)
    assert bt["checks"][0]["q"][0] == pytest.approx(math.log(1.035), rel=1e-6)
