import json

import numpy as np
import pandas as pd
import pytest

from nordic_desk import ohlc, prices
from nordic_desk.analysis import Subject
from nordic_desk.forecasts import WARNING, build_forecasts

IDX = pd.bdate_range("2019-01-01", periods=1500)
FUND = {"AAA": ("EQUITY", "USD"), "BBB.DE": ("EQUITY", "EUR"), "CCC.ST": ("EQUITY", "SEK"), "^IDX": ("INDEX", "EUR")}


@pytest.fixture
def roots(tmp_path):
    rng = np.random.default_rng(7)
    pr, oh, fu = tmp_path / "prices", tmp_path / "ohlc", tmp_path / "fund"
    fu.mkdir()
    series = {t: pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, len(IDX)))), index=IDX) for t in [*FUND, "SPY"]}
    series["EURUSD=X"] = pd.Series(1.1, index=IDX)
    for t, s in series.items():
        prices.update([t], root=pr, fetch=lambda tk, st, s=s: s)
        if t in FUND:
            ohlc.update_ohlc([t], root=oh, fetch=lambda tk, st, s=s: pd.DataFrame({"open": s, "high": s * 1.01, "low": s * 0.99, "close": s}))
            qt, cur = FUND[t]
            (fu / f"{prices._file(t, fu).stem}.json").write_text(json.dumps({"quote_type": qt, "currency": cur}), encoding="utf-8")
    hist = tmp_path / "hist.csv"
    hist.write_text("date,ticker,price,target_mean\n2023-01-03,AAA,100,130\n2023-01-20,AAA,100,130\n", encoding="utf-8")
    return pr, oh, fu, hist, tmp_path


def make(roots, cards=None):
    pr, oh, fu, hist, tmp = roots
    subs = [Subject(t, t, ("watch",), "") for t in FUND]
    desk = {"forecast": {"backtest": {"n": 240, "hits": 13, "rate": 0.054, "expected": 0.05, "p_value": 0.6}}}
    cards = cards or {"cards": {"AAA": {"ticker": "AAA", "name": "Example A", "currency": "USD", "analysts": {"target_mean": 130.0, "upside": 0.3}}}}
    return build_forecasts(subs, desk, cards, pr, oh, fu, hist, tmp / "none.toml")


def test_excludes_other_currency_and_index(roots):
    d = make(roots)
    why = {e["ticker"]: e["why"] for e in d["excluded"]}
    assert set(why) == {"CCC.ST", "^IDX"} and "SEK" in why["CCC.ST"] and "index" in why["^IDX"]


def test_json_has_no_nan(roots):
    json.dumps(make(roots), allow_nan=False)


def test_horizons_present_and_per_stock_keys(roots):
    sc = make(roots)["scorecard"]
    assert set(sc) == {"63", "126", "252"}
    assert set(sc["126"]["per_stock"]) == {"AAA", "BBB.DE"}
    g = next(iter(sc["126"]["groups"].values()))
    assert {"n_months", "mean", "lo", "hi", "reading", "label"} <= set(g)


def test_lump_for_spy_and_stock(roots):
    lump = make(roots)["lump"]
    assert set(lump) == {"AAA", "BBB.DE", "SPY"} and lump["SPY"]["6"]["starts"] > 0 and set(lump["AAA"]) == {"3", "6", "12"}


def test_targets_rows_from_cards_and_study_rates(roots):
    t = make(roots)["targets"]
    row = t["rows"][0]
    assert row["ticker"] == "AAA" and row["realistic"] == pytest.approx(0.15) and row["price"] == pytest.approx(100.0)
    assert row["currency"] == "USD"
    assert t["rates"]["source"].startswith("Bradshaw") and t["rates"]["n_checked"] == 1  # two January rows count once


def test_warning_text_verbatim(roots):
    assert make(roots)["warning"] == WARNING == ("Stocks are the ones you hold or watch today; past winners are over-represented, "
                                                 "so these numbers flatter the signals.")


def test_today_verdict_per_stock(roots):
    today = make(roots)["today"]
    assert set(today) == {"AAA", "BBB.DE"}
    assert today["AAA"]["group"] in {"pullback", "steady", "stretched", "wait_down", "wait_mixed", None}
    assert today["AAA"]["date"] == "2024-10-01" or len(today["AAA"]["date"]) == 10


def test_expected_and_volsize_keys(roots):
    d = make(roots)
    json.dumps(d, allow_nan=False)
    assert d["anchor"]["rate"] is not None and set(d["expected"]) == {"AAA", "BBB.DE"}
    e = d["expected"]["AAA"]
    assert e["analyst"] == pytest.approx(0.15) and e["pieces"] >= 1
    assert set(d["volsize"]) == {"AAA", "BBB.DE", "SPY"} and set(d["volsize"]["AAA"]) == {"now", "3", "6", "12"}
