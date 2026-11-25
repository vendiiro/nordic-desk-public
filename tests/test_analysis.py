import json

import numpy as np
import pandas as pd
import pytest

from nordic_desk.analysis import Subject, analysis_href, kind_of, payload, slug, subjects
from nordic_desk.analysis_config import load
from nordic_desk.explain import FIELDS_USED
from nordic_desk.verdict import VERDICT_TABLE

CFG = load()
FX = {"USD": 1.0, "EUR": 1.1}
STOCK = {"ticker": "EXMPL", "name": "Example Corp", "quote_type": "EQUITY", "currency": "USD", "financial_currency": "USD",
         "sector": "Technology", "returnOnEquity": 0.2, "profitMargins": 0.15, "debtToEquity": 80.0, "freeCashflow": 4e9,
         "revenueGrowth": 0.05, "marketCap": 1e11,
         "eps": [{"year_end": f"{y}-12-31", "eps": 2.0 + 0.3 * (y - 2018)} for y in range(2018, 2026)]}
SUBJ = Subject("EXMPL", "Example Corp", ("watch",), "")


def ohlc(n=1500, seed=3, start="2020-01-01"):
    rng = np.random.default_rng(seed)
    c = pd.Series(50 * np.exp(np.cumsum(rng.normal(0.0006, 0.015, n))), index=pd.bdate_range(start, periods=n))
    return pd.DataFrame({"open": c * 0.998, "high": c * 1.01, "low": c * 0.99, "close": c})


def make(df=None, f=STOCK, s=SUBJ, fallback=None):
    df = ohlc() if df is None else df
    return payload(s, df, df["close"] if fallback is None else fallback, f, CFG, FX, "2026-11-20")


def test_slug_and_href():
    assert slug("^OMXH25") == "_OMXH25" and slug("EURUSD=X") == "EURUSD_X" and slug("BRK-B") == "BRK-B"
    assert analysis_href("ETH-EUR") is None and analysis_href("CBUT.DE") is None
    assert analysis_href("^OMXH25") == "analysis/_OMXH25.html"


def _toml(tmp_path, holdings, instruments):
    h, i = tmp_path / "h.toml", tmp_path / "i.toml"
    h.write_text(holdings, encoding="utf-8")
    i.write_text(instruments, encoding="utf-8")
    return h, i


HOLD = """as_of = 2026-01-15
cash_eur = 10.0
[[position]]
name = "Example Corp"
ticker = "EXMPL"
quantity = 1
value_eur = 100.0
[[position]]
name = "Example Index Fund"
ticker = "^OMXH25"
quantity = 1
value_eur = 100.0
[[position]]
name = "Crypto tracker"
ticker = "CBUT.DE"
quantity = 1
value_eur = 100.0
[[position]]
name = "No ticker"
quantity = 1
value_eur = 100.0
"""
INSTR = """["Example Index Fund"]
ticker = "^OMXH25"
currency = "EUR"
note = "Index stands in for the fund."
"""


def test_subjects_merge_groups_and_drop_crypto(tmp_path):
    h, i = _toml(tmp_path, HOLD, INSTR)
    cards = {"cards": [{"ticker": "NEWCO", "name": "New Co"}, {"ticker": "EXMPL", "name": "Example Corp"}]}
    subs = {s.ticker: s for s in subjects(h, i, ["EXMPL", "AAPL"], cards)}
    assert set(subs) == {"EXMPL", "^OMXH25", "AAPL", "NEWCO"}
    assert subs["EXMPL"].groups == ("held", "watch", "idea") and subs["NEWCO"].name == "New Co"


def test_standin_note_and_name(tmp_path):
    h, i = _toml(tmp_path, HOLD, INSTR)
    s = {s.ticker: s for s in subjects(h, i, [], None)}["^OMXH25"]
    assert s.name == "Example Index Fund" and s.note == "Index stands in for the fund."


def test_subjects_without_holdings_file(tmp_path):
    assert [s.ticker for s in subjects(tmp_path / "missing.toml", tmp_path / "missing.toml", ["AAPL"], None)] == ["AAPL"]


def test_kind_of():
    assert kind_of(STOCK) == "stock" and kind_of({"quote_type": "INDEX"}) == "fund" and kind_of(None) == "unknown"
    assert kind_of({"quote_type": "CRYPTOCURRENCY"}) == "crypto"


def test_payload_json_has_no_nan():
    json.dumps(make(), allow_nan=False)


def test_payload_fields_cover_explain_templates():
    assert FIELDS_USED <= set(make())


def test_payload_window_and_lengths():
    p = make()
    assert len(p["dates"]) == 1260 and all(len(p[k]) == 1260 for k in ("c", "o", "sma200", "pe", "entry_day", "long_day", "trend"))
    assert p["verdicts"] == [{"v": v, "cls": c, "line": l} for v, c, l in VERDICT_TABLE]


def test_payload_without_ohlc_falls_back_to_line():
    df = ohlc()
    p = make(df=df.iloc[0:0], fallback=df["close"])
    assert not p["has_ohlc"] and p["defaults"]["entry"]["style"] == "line" and all(v is None for v in p["o"])
    short = ohlc(300)
    json.dumps(make(df=short.iloc[0:0], fallback=short["close"], f=None), allow_nan=False)  # warm-up trend stays None, not NaN
    assert p["c"][-1] == pytest.approx(df["close"].iloc[-1], rel=1e-4)


def test_fund_has_no_long_verdict_and_says_not_available():
    p = make(f={"quote_type": "ETF", "currency": "USD"})
    assert p["today"]["long"] is None and p["kind"] == "fund" and set(p["long_day"]) == {None}
    assert "pe" not in p["defaults"]["long"]["on"] and all(v is None for v in p["pe"])
    assert {b["value"] for b in p["boxes"]["long"][:2]} == {"not available for funds"}


def test_today_verdict_matches_last_entry_day():
    p = make()
    assert p["verdicts"][p["entry_day"][-1]]["v"] == p["today"]["entry"]["v"]
    assert p["today"]["long"]["v"] in ("Attractive", "Fair", "Expensive") and p["quality"]["score"] == 100


def test_short_history_payload():
    p = make(df=ohlc(150))
    json.dumps(p, allow_nan=False)
    assert len(p["dates"]) == 150 and p["today"]["entry"]["line"] == "Not enough history yet"


def test_other_currency_earnings_give_no_pe():
    p = make(f={**STOCK, "financial_currency": "DKK"})
    assert p["pe_reason"] == "earnings reported in another currency" and all(v is None for v in p["pe"])
    assert p["today"]["long"]["line"] == "P/E not available: earnings reported in another currency"


def test_subjects_reads_cards_dict(tmp_path):
    h, i = _toml(tmp_path, HOLD, INSTR)
    subs = {s.ticker: s for s in subjects(h, i, [], {"cards": {"XLV": {"ticker": "XLV", "name": "Health ETF"}}})}
    assert subs["XLV"].name == "Health ETF" and subs["XLV"].groups == ("idea",)


def test_stretch_box_reflects_overbought_rsi():
    c = pd.Series(np.linspace(50, 150, 400), index=pd.bdate_range("2024-01-01", periods=400))
    df = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c})
    box = make(df=df)["boxes"]["entry"][1]
    assert box["key"] == "bb" and "overbought" in box["text"].lower()


def test_missing_company_data_is_not_called_a_fund():
    p = make(f=None)
    assert p["kind"] == "unknown" and p["today"]["long"] is None
    assert "not available for funds" not in str(p["boxes"]["long"]) and "nordic-desk update" in str(p["boxes"]["long"])


def test_pe_uses_split_only_ohlc_close_not_adjusted_fallback():
    df = ohlc()
    p = make(df=df.iloc[0:0], fallback=df["close"])  # only dividend-adjusted closes available
    assert p["pe_reason"] == "no split-only price history" and all(v is None for v in p["pe"])


def test_payload_track_from_forecasts():
    per_stock = {"EXMPL": {g: {"n_months": 30, "beat": 0.5, "mean": 0.0, "lo": -0.01, "hi": 0.01, "since": "2016",
                               "reading": "too noisy to trust alone", "label": g} for g in ("pullback", "steady", "stretched", "wait_down", "wait_mixed")}}
    p = make()
    from nordic_desk.analysis import track_for
    t = track_for(p["today"]["entry"]["line"], per_stock.get("EXMPL"))
    assert t is None or t["stats"]["n_months"] == 30
    assert track_for("Not enough history yet", per_stock["EXMPL"]) is None and track_for("Trend is down", None) is None
    assert track_for("Trend is down", {})["stats"] is None


def test_index_row_from_payload():
    from nordic_desk.analysis import index_row
    p = make()
    r = index_row(p)
    assert r["ticker"] == "EXMPL" and r["group"] == "watch" and r["price"] == pytest.approx(p["c"][-1])
    assert r["verdict"] == p["today"]["entry"]["v"] and r["cls"] == p["today"]["entry"]["cls"]
    assert r["rsi"] == p["rsi"][-1] and r["mom"] == p["mom"][-1] and len(r["spark"]) == 63
    assert 0 <= r["pos52"] <= 1 and r["d1"] == pytest.approx(p["c"][-1] / p["c"][-2] - 1)
    json.dumps(r, allow_nan=False)


def test_verdict_changes_survive_a_rebuild_on_the_same_close():
    from nordic_desk.analysis import remember
    rows = lambda v: [{"ticker": "EXMPL", "verdict": v, "cls": "good", "line": "x", "expected": None, "name": "E", "group": "watch"}]
    old = {"EXMPL": "Wait"}  # file format before the close date was stored
    doc = remember(old, rows("Good entry"), "2026-11-23")
    assert doc["rows"]["EXMPL"]["changed"] is True
    again = remember(doc, rows("Good entry"), "2026-11-23")  # site run twice, or brief after site
    assert again["rows"]["EXMPL"]["changed"] is True
    next_day = remember(again, rows("Good entry"), "2026-11-24")
    assert next_day["rows"]["EXMPL"]["changed"] is False
