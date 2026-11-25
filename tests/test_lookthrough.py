import pytest

from nordic_desk.lookthrough import company_key, fund_holdings, look_through, share_after

FUND = {"ticker": "QQQ", "covered": 0.18, "holdings": [
    {"symbol": "MSFT", "name": "Microsoft", "weight": 0.10}, {"symbol": "NVDA", "name": "NVIDIA", "weight": 0.08}]}


def test_company_key_variants():
    assert company_key("ASML.AS") == "ASML"
    assert company_key("NOKIA.HE") == "NOKIA.HE"
    assert company_key("GOOG") == "GOOGL"
    assert company_key("BRK-B") == "BRK-B"


def test_foreign_listing_not_merged_with_us_ticker():
    assert company_key("ROP.SW") != company_key("ROP")  # Roche (Swiss) is not Roper Technologies
    assert company_key("EL.PA") != company_key("EL")    # EssilorLuxottica is not Estee Lauder


def test_direct_plus_fund():
    lt = look_through({"MSFT": 1000.0, "QQQ": 2000.0}, 0.0, {"MSFT": None, "QQQ": FUND})
    m = lt["companies"]["MSFT"]
    assert (m["direct"], m["via_funds"], m["value"]) == (1000.0, pytest.approx(200.0), pytest.approx(1200.0))
    assert m["share"] == pytest.approx(0.4)
    assert m["funds"] == {"QQQ": pytest.approx(200.0)}
    assert lt["companies"]["NVDA"]["share"] == pytest.approx(160 / 3000)
    assert lt["not_broken_down"] == pytest.approx(2000 * 0.82)
    assert lt["total"] == 3000.0


def test_share_after_stock_purchase():
    after = share_after({"MSFT": 1000.0, "QQQ": 2000.0}, 0.0, {"MSFT": None, "QQQ": FUND}, "NVDA", 1000.0, None)
    assert after["companies"]["NVDA"]["share"] == pytest.approx(1160 / 4000)


def test_share_after_fund_purchase():
    after = share_after({"MSFT": 1000.0}, 0.0, {"MSFT": None}, "QQQ", 1000.0, FUND)
    assert after["companies"]["MSFT"]["value"] == pytest.approx(1100.0)
    assert after["companies"]["NVDA"]["value"] == pytest.approx(80.0)


def test_symbol_variants_match():
    f = {"ticker": "F", "covered": 0.2, "holdings": [{"symbol": "ASML.AS", "name": "ASML", "weight": 0.1},
                                                     {"symbol": "GOOG", "name": "Alphabet C", "weight": 0.1}]}
    lt = look_through({"ASML": 500.0, "GOOGL": 500.0, "F": 1000.0}, 0.0, {"F": f})
    assert lt["companies"]["ASML"]["value"] == pytest.approx(600.0)
    assert lt["companies"]["GOOGL"]["value"] == pytest.approx(600.0)


def test_fund_without_data_not_guessed():
    nd = {"ticker": "^OMXH25", "holdings": [], "covered": 0.0, "no_data": True}
    lt = look_through({"MSFT": 1000.0, "^OMXH25": 500.0}, 100.0, {"^OMXH25": nd})
    assert lt["no_data"] == ["^OMXH25"] and lt["not_broken_down"] == 500.0
    assert "OMXH25" not in lt["companies"] and "^OMXH25" not in lt["companies"]
    assert lt["total"] == 1600.0


class Fetch:
    def __init__(self, result=None, error=None):
        self.calls, self.result, self.error = 0, result, error

    def __call__(self, t):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


ROWS = [{"symbol": "MSFT", "name": "Microsoft", "weight": 0.1}, {"symbol": "NVDA", "name": "NVIDIA", "weight": 0.08}]


def test_fund_cached_within_a_day(tmp_path):
    f = Fetch(ROWS)
    a = fund_holdings("QQQ", cache_dir=tmp_path, fetch=f)
    b = fund_holdings("QQQ", cache_dir=tmp_path, fetch=f)
    assert f.calls == 1 and a["covered"] == pytest.approx(0.18) and b["holdings"] == ROWS


def test_not_a_fund_cached(tmp_path):
    f = Fetch(error=LookupError("no fund data"))
    assert fund_holdings("MSFT", cache_dir=tmp_path, fetch=f) is None
    assert fund_holdings("MSFT", cache_dir=tmp_path, fetch=f) is None
    assert f.calls == 1


def test_fetch_error_not_cached(tmp_path):
    with pytest.raises(RuntimeError):
        fund_holdings("QQQ", cache_dir=tmp_path, fetch=Fetch(error=RuntimeError("down")))
    ok = Fetch(ROWS)
    assert fund_holdings("QQQ", cache_dir=tmp_path, fetch=ok)["holdings"] == ROWS and ok.calls == 1


def test_index_ticker_skips_fetch(tmp_path):
    f = Fetch(ROWS)
    d = fund_holdings("^OMXH25", cache_dir=tmp_path, fetch=f)
    assert d["no_data"] is True and d["holdings"] == [] and f.calls == 0


def test_percent_weights_rejected(tmp_path):
    rows = [{"symbol": "MSFT", "name": "Microsoft", "weight": 10.0}, {"symbol": "NVDA", "name": "NVIDIA", "weight": 8.0}]
    with pytest.raises(ValueError):
        fund_holdings("QQQ", cache_dir=tmp_path, fetch=Fetch(rows))


def test_resolve_funds_uses_stand_in_and_marks_gaps():
    from nordic_desk.lookthrough import resolve_funds
    asked = []

    def get_fund(t):
        asked.append(t)
        if t == "BAD":
            raise RuntimeError("down")
        return FUND if t == "XLK" else None

    funds = resolve_funds(["FUNDA.DE", "MSFT", "BAD"], get_fund, {"FUNDA.DE": "XLK"})
    assert asked == ["XLK", "MSFT", "BAD"]
    assert funds["FUNDA.DE"] is FUND and funds["MSFT"] is None
    assert funds["BAD"] == {"ticker": "BAD", "holdings": [], "covered": 0.0, "no_data": True}


def test_top_companies_shares_only():
    from nordic_desk.lookthrough import top_companies
    lt = look_through({"MSFT": 1000.0, "QQQ": 2000.0, "A": 10.0, "B": 9.0, "C": 8.0, "D": 7.0}, 0.0, {"QQQ": FUND})
    top = top_companies(lt, n=5)
    assert [r["key"] for r in top["top"]] == ["MSFT", "NVDA", "A", "B", "C"]
    m = top["top"][0]
    assert m["share"] == pytest.approx(1200 / 3034, abs=1e-4)
    assert m["direct"] == pytest.approx(1000 / 3034, abs=1e-4) and m["via_funds"] == pytest.approx(200 / 3034, abs=1e-4)
    assert set(m) == {"key", "name", "share", "direct", "via_funds"}
    assert top["not_broken_down"] == pytest.approx(1640 / 3034, abs=1e-4)
    assert top["no_data"] == [] and "Yahoo" in top["source"]


def test_portfolio_lookthrough_from_files(tmp_path):
    from nordic_desk.lookthrough import portfolio_lookthrough
    inst = tmp_path / "inst.toml"
    inst.write_text('["Nordnet Suomi Indeksi"]\nticker = "^OMXH25"\ncurrency = "EUR"\nholdings_from = "XLK"\n', encoding="utf-8")
    xlk = {"ticker": "XLK", "covered": 0.2, "holdings": [{"symbol": "MSFT", "name": "Microsoft", "weight": 0.2}]}
    block = portfolio_lookthrough("config/holdings.example.toml", inst, lambda t: xlk if t == "XLK" else None)
    top = block["top"][0]
    assert top["key"] == "MSFT" and top["via_funds"] == pytest.approx(1200 * 0.2 / 3250, abs=1e-4)
    assert block["no_data"] == []


def test_format_top():
    from nordic_desk.lookthrough import format_top
    text = format_top({"top": [{"key": "MSFT", "name": "Microsoft", "share": 0.4, "direct": 0.33, "via_funds": 0.07}],
                       "not_broken_down": 0.2, "no_data": ["^OMXH25"], "source": "Yahoo Finance fund top holdings"})
    assert text.splitlines()[0] == "Largest companies, including funds"
    assert "Microsoft" in text and "40.0%" in text and "7.0% through funds" in text
    assert "20% not broken down" in text and "^OMXH25" in text


def test_direct_holding_named_from_report(tmp_path):
    from nordic_desk.lookthrough import portfolio_lookthrough
    inst = tmp_path / "inst.toml"
    inst.write_text('["Microsoft"]\nticker = "MSFT"\ncurrency = "USD"\n', encoding="utf-8")
    block = portfolio_lookthrough("config/holdings.example.toml", inst, lambda t: None)
    assert block["top"][0]["key"] == "MSFT" and block["top"][0]["name"] == "Microsoft"


def test_fund_without_published_holdings_is_no_data(tmp_path):
    f = Fetch([])
    d = fund_holdings("BONDX", cache_dir=tmp_path, fetch=f)
    assert d["no_data"] is True and d["holdings"] == [] and d["covered"] == 0.0
    assert fund_holdings("BONDX", cache_dir=tmp_path, fetch=f)["no_data"] is True and f.calls == 1


class FakeTicker:
    def __init__(self, quote_type):
        self.info = {"quoteType": quote_type}

    @property
    def funds_data(self):
        raise RuntimeError("No Fund data found for ticker")


def test_yahoo_fund_without_data_returns_empty(monkeypatch):
    monkeypatch.undo()  # the conftest stub replaces this function; the fake Ticker below keeps it off the network
    from nordic_desk.lookthrough import yf_top_holdings
    assert yf_top_holdings("BONDX", ticker_cls=lambda t: FakeTicker("ETF")) == []
    with pytest.raises(LookupError):
        yf_top_holdings("MSFT", ticker_cls=lambda t: FakeTicker("EQUITY"))
