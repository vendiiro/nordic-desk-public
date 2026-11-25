import numpy as np
import pytest
import pandas as pd

from nordic_desk.plan import plan_allocation

N = 252
A = np.tile([0.01, -0.01, 0.01, -0.01], N // 4)
B = np.tile([0.01, 0.01, -0.01, -0.01], N // 4)   # uncorrelated with A


def panel(**r):
    idx = pd.bdate_range("2025-01-01", periods=N + 1)
    return pd.DataFrame({k: 100 * np.concatenate([[1.0], np.cumprod(1 + v)]) for k, v in r.items()}, index=idx)


def test_money_goes_to_the_diversifier_and_tech_falls():
    p = panel(A=A, B=B, C=A, SPY=A)
    out = plan_allocation(p, {"A": 1000.0}, 0.0, tech={"A", "C"}, candidates=["B", "C"], amount=1000, step=500, tech_max=0.5)
    assert out["split"] == {"B": 1000.0}
    assert out["after"]["vol"] < out["before"]["vol"] and out["after"]["tech"] < out["before"]["tech"]


def test_tech_cap_blocks_tech_candidate():
    p = panel(A=B, C=A, SPY=A)                       # the tech candidate C would diversify, but tech is capped
    out = plan_allocation(p, {"A": 1000.0}, 0.0, tech={"C"}, candidates=["C"], amount=1000, step=500, tech_max=0.2)
    assert out["split"] == {} and "cap" in out["note"]


def test_run_plan_writes_json(tmp_path):
    import json
    from nordic_desk import prices
    from nordic_desk.plan import run_plan
    idx = pd.bdate_range("2024-06-03", "2026-01-14")
    rng = np.random.default_rng(3)
    root = tmp_path / "prices"
    for t in ["MSFT", "^OMXH25", "SPY", "XLV", "AMD"]:
        v = 100 * np.cumprod(1 + rng.normal(0, 0.01, len(idx)))
        prices.update([t], root=root, fetch=lambda tk, s, v=v: pd.Series(v, index=idx))
    prices.update(["EURUSD=X"], root=root, fetch=lambda tk, s: pd.Series(np.full(len(idx), 1.1), index=idx))
    info = {"XLV": {"currency": "USD", "sector": None}, "AMD": {"currency": "USD", "sector": "Technology"},
            "NOPRICE": {"currency": "USD", "sector": None}}
    out = run_plan(1000, ["XLV", "AMD", "NOPRICE"], info, out_dir=tmp_path / "out", price_root=root,
                   holdings_path="config/holdings.example.toml", end="2026-01-14")
    saved = json.loads((tmp_path / "out" / "plan.json").read_text(encoding="utf-8"))
    assert sum(saved["split"].values()) == 1000 and saved["skipped"] == ["NOPRICE"]
    assert out["after"]["vol"] <= out["before"]["vol"]


def test_plan_section_on_ideas_page():
    from nordic_desk.views.cards import cards_page
    plan = {"split": {"XLV": 3000.0, "PG": 2000.0}, "note": "", "amount": 5000, "tech_max": 0.5, "skipped": [],
            "before": {"vol": 0.2, "beta": 1.1, "worst": -0.17, "tech": 0.62, "enb": 5.1},
            "after": {"vol": 0.185, "beta": 1.0, "worst": -0.15, "tech": 0.55, "enb": 6.0}}
    html = cards_page({"meta": {"close": "2026-01-14", "built": "x"}, "groups": {}, "cards": {}, "errors": {}}, plan=plan)
    assert "Suggested split" in html and "XLV" in html and "62.0%" in html and "55.0%" in html


C2 = np.tile([0.01, -0.01, -0.01, 0.01], N // 4)   # uncorrelated with A and B


def test_optimiser_splits_between_equal_diversifiers():
    from nordic_desk.plan import optimise_allocation
    p = panel(A=A, B=B, C=C2, SPY=A)
    out = optimise_allocation(p, {"A": 1000.0}, 0.0, tech={"A"}, candidates=["B", "C"], amount=1000, tech_max=0.5)
    assert sum(out["split"].values()) == pytest.approx(1000, abs=1)
    assert out["split"]["B"] == pytest.approx(500, abs=30) and out["split"]["C"] == pytest.approx(500, abs=30)
    assert out["after"]["vol"] < out["before"]["vol"]


def test_optimiser_respects_tech_cap():
    from nordic_desk.plan import optimise_allocation
    p = panel(A=A, B=B, C=C2, SPY=A)
    out = optimise_allocation(p, {"A": 1000.0}, 1000.0, tech={"C"}, candidates=["B", "C"], amount=1000, tech_max=0.1)
    assert out["after"]["tech"] <= 0.1 + 1e-6


def test_plan_section_shows_optimiser():
    from nordic_desk.views.cards import cards_page
    stats = {"vol": 0.2, "beta": 1.1, "worst": -0.17, "tech": 0.62, "enb": 5.1}
    plan = {"split": {"XLV": 5000.0}, "note": "", "amount": 5000, "tech_max": 0.5, "skipped": [], "before": stats, "after": stats,
            "optimised": {"split": {"XLE": 2600.0, "PG": 2400.0}, "note": "", "amount": 5000, "tech_max": 0.5, "before": stats,
                          "after": dict(stats, vol=0.17)}}
    html = cards_page({"meta": {"close": "2026-01-14", "built": "x"}, "groups": {}, "cards": {}, "errors": {}}, plan=plan)
    assert "Optimiser" in html and "XLE" in html and "17.0%" in html


def test_optimiser_moves_away_from_equal_split_at_real_scale():
    from nordic_desk.plan import optimise_allocation
    p = panel(A=A, B=B, C=A, SPY=A)        # C moves with the holding, B does not: all money belongs in B
    out = optimise_allocation(p, {"A": 30000.0}, 0.0, tech=set(), candidates=["B", "C"], amount=5000, tech_max=0.5)
    assert out["split"].get("B", 0) > 4800
