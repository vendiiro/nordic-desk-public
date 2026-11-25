import json

import pandas as pd

from nordic_desk.fundamentals import eps_available, fetch_fundamentals, load_fundamentals, pe_reason, update_fundamentals

INFO = {"quoteType": "EQUITY", "currency": "USD", "financialCurrency": "USD", "shortName": "Example Corp", "sector": "Technology",
        "returnOnEquity": 0.21, "profitMargins": 0.17, "debtToEquity": 45.0, "freeCashflow": 5e9, "revenueGrowth": 0.08,
        "marketCap": 1.2e11}
EPS = [{"year_end": "2024-12-31", "eps": 2.0}, {"year_end": "2023-12-31", "eps": 1.5}]


def test_eps_available_lags_90_days():
    assert eps_available(EPS, 90) == [(pd.Timestamp("2024-03-30"), 1.5), (pd.Timestamp("2025-03-31"), 2.0)]


def test_pe_reason_other_currency():
    f = {"quote_type": "EQUITY", "currency": "USD", "financial_currency": "DKK", "eps": EPS}
    assert pe_reason(f) == "earnings reported in another currency"


def test_pe_reason_fund_and_empty():
    assert pe_reason({"quote_type": "ETF", "eps": []}) == "not a company (fund or index)"
    assert pe_reason({"quote_type": "EQUITY", "currency": "USD", "financial_currency": "USD", "eps": []}) == "no earnings history"
    assert pe_reason(None) == "no earnings history"
    assert pe_reason({"quote_type": "EQUITY", "currency": "USD", "financial_currency": "USD", "eps": EPS}) is None


def test_fetch_maps_fields_and_drops_non_finite():
    f = fetch_fundamentals("EXMPL", fetch_info=lambda t: {**INFO, "revenueGrowth": float("nan")}, fetch_eps=lambda t: EPS)
    assert f["quote_type"] == "EQUITY" and f["name"] == "Example Corp" and f["returnOnEquity"] == 0.21
    assert f["revenueGrowth"] is None and f["eps"] == EPS


def test_update_writes_and_keeps_old_on_error(tmp_path):
    ok = lambda t: fetch_fundamentals(t, fetch_info=lambda _: INFO, fetch_eps=lambda _: EPS)
    assert update_fundamentals(["^X"], root=tmp_path, fetch=ok) == {"^X": "ok"}
    before = load_fundamentals("^X", tmp_path)

    def boom(t):
        raise RuntimeError("down")

    st = update_fundamentals(["^X"], root=tmp_path, fetch=boom)
    assert st["^X"].startswith("error:") and load_fundamentals("^X", tmp_path) == before
    assert load_fundamentals("NOPE", tmp_path) is None
    json.dumps(before, allow_nan=False)


def test_update_keeps_old_file_when_yahoo_returns_nothing(tmp_path):
    ok = lambda t: fetch_fundamentals(t, fetch_info=lambda _: INFO, fetch_eps=lambda _: EPS)
    update_fundamentals(["X"], root=tmp_path, fetch=ok)
    empty = lambda t: fetch_fundamentals(t, fetch_info=lambda _: {}, fetch_eps=lambda _: [])
    st = update_fundamentals(["X"], root=tmp_path, fetch=empty)
    assert st["X"].startswith("error:") and load_fundamentals("X", tmp_path)["quote_type"] == "EQUITY"
