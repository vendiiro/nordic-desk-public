import numpy as np
import pandas as pd
import pytest

from nordic_desk import prices
from nordic_desk.cards import build_card

END = "2026-01-14"


@pytest.fixture
def store(tmp_path):
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2023-06-01", END)
    root = tmp_path / "prices"
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0004, 0.015, len(idx))) for t in ["MSFT", "^OMXH25", "SPY", "LLY", "ETFX"]}
    data["EURUSD=X"] = np.full(len(idx), 1.1)
    for t, v in data.items():
        prices.update([t], root=root, fetch=lambda tk, s, v=v: pd.Series(v, index=idx))
    young = pd.bdate_range("2025-10-01", END)
    prices.update(["NEW"], root=root, fetch=lambda tk, s: pd.Series(np.linspace(10, 12, len(young)), index=young))
    return root


def cand(ticker, sector="Healthcare", target=None, n=20, qtype="EQUITY"):
    return {"ticker": ticker, "name": ticker, "sector": sector, "industry": "x", "currency": "USD", "quote_type": qtype,
            "market_cap": 5e9, "target_mean": target, "target_low": None, "target_high": None, "n_analysts": n,
            "rating_counts": {"strongBuy": 2, "buy": 6, "hold": 2, "sell": 0, "strongSell": 0}, "results": []}


def card(store, data, analysts=None, **kw):
    return build_card(data["ticker"], data, holdings_path="config/holdings.example.toml", price_root=store, end=END,
                      analysts=analysts or {}, **kw)


NO_DATA = {"ticker": "^OMXH25", "holdings": [], "covered": 0.0, "no_data": True}


def test_impact_per_amount(store):
    c = card(store, cand("LLY"), amounts=(1000, 2000))
    assert set(c["impact"]["amounts"]) == {"1000", "2000"}
    a = c["impact"]["amounts"]["1000"]
    assert {"vol", "beta", "worst", "enb", "tech", "expected"} <= set(a)
    assert -1 <= c["impact"]["corr"] <= 1


def test_short_history_has_no_impact(store):
    c = card(store, cand("NEW"))
    assert c["impact"] is None and "not enough price history" in c["impact_note"]


def test_tech_from_sector(store):
    health = card(store, cand("LLY"))["impact"]["amounts"]["1000"]["tech"]
    tech = card(store, cand("LLY", sector="Technology"))["impact"]["amounts"]["1000"]["tech"]
    assert tech > health


def test_analyst_block_and_expected_return(store):
    last = prices.load("LLY", root=store).iloc[-1]
    c = card(store, cand("LLY", target=last * 1.3), analysts={"MSFT": {"upside": 0.10}})
    a = c["analysts"]
    assert a["upside"] == pytest.approx(0.3) and a["status"] == "below buy threshold"
    assert a["rating_share"] == pytest.approx(0.8)
    e = c["impact"]["expected_before"], c["impact"]["amounts"]["5000"]["expected"]
    assert e[0]["value"] == pytest.approx(0.10) and e[1]["value"] > e[0]["value"]


def test_short_history_has_no_chart(store):
    c = card(store, cand("NEW"))
    assert c["price"] is None and "not enough price history" in c["price_note"]


def test_sek_listing_gets_comparison(store):
    idx = pd.bdate_range("2023-06-01", END)
    prices.update(["EURSEK=X"], root=store, fetch=lambda tk, s: pd.Series(np.full(len(idx), 11.0), index=idx))
    d = cand("LLY")
    d["currency"] = "SEK"
    assert card(store, d)["impact"] is not None


def test_pence_listing_uses_pound_rate(store):
    idx = pd.bdate_range("2023-06-01", END)
    prices.update(["EURGBP=X"], root=store, fetch=lambda tk, s: pd.Series(np.full(len(idx), 0.85), index=idx))
    d = cand("LLY")
    d["currency"] = "GBp"
    assert card(store, d)["impact"] is not None


def test_lookthrough_on_stock_card(store):
    c = card(store, cand("LLY"), amounts=(1000, 2000), funds={"MSFT": None, "^OMXH25": NO_DATA})
    lt = c["lookthrough"]
    assert lt["focus"] == ["LLY"] and lt["names"]["LLY"] == "LLY"
    assert lt["before"]["LLY"] == 0.0 and lt["via_funds"]["LLY"] == 0.0
    assert lt["amounts"]["2000"]["LLY"] == pytest.approx(2000 / 5250, abs=1e-4)  # example: 1800 + 1200 + cash 250
    assert lt["no_data"] == ["^OMXH25"]
    assert lt["not_broken_down"] == pytest.approx(1200 / 3250, abs=1e-4)


def test_lookthrough_on_fund_card(store):
    fund = {"ticker": "ETFX", "covered": 0.5, "holdings": [{"symbol": "MSFT", "name": "Microsoft", "weight": 0.3},
                                                          {"symbol": "LLY", "name": "Eli Lilly", "weight": 0.2}]}
    c = card(store, cand("ETFX", qtype="ETF"), amounts=(1000, 2000), funds={"MSFT": None, "^OMXH25": NO_DATA}, cand_fund=fund)
    lt = c["lookthrough"]
    assert lt["focus"] == ["MSFT", "LLY"] and lt["names"]["MSFT"] == "Microsoft"
    assert lt["amounts"]["2000"]["MSFT"] == pytest.approx((1800 + 600) / 5250, abs=1e-4)
    assert lt["amounts"]["2000"]["LLY"] == pytest.approx(400 / 5250, abs=1e-4)
    assert lt["via_funds"] == {"MSFT": 0.0, "LLY": 0.0}


def test_no_lookthrough_without_funds(store):
    assert card(store, cand("LLY"))["lookthrough"] is None
    assert card(store, cand("NEW"), funds={})["lookthrough"] is None  # no impact, no look-through


def test_card_amounts_from_config(tmp_path):
    from nordic_desk.cards import load_card_amounts

    p = tmp_path / "t.toml"
    p.write_text('card_amounts = [3000, 2000]' + chr(10) + 'card_default = 3000' + chr(10), encoding="utf-8")
    assert load_card_amounts(p) == ((2000, 3000), 3000)
    p.write_text('step = 500' + chr(10), encoding="utf-8")
    assert load_card_amounts(p) == ((500, 1000, 2500, 5000), 1000)
    p.write_text('card_amounts = [2000]' + chr(10) + 'card_default = 3000' + chr(10), encoding="utf-8")
    with pytest.raises(ValueError):
        load_card_amounts(p)
