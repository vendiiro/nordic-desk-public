from datetime import date
from pathlib import Path

from nordic_desk.config import load_holdings, load_instruments, load_watchlist


def test_watchlist_loads():
    tickers = load_watchlist()
    assert len(tickers) == 13
    assert "ORCL" in tickers


def test_instrument_stand_in():
    inst = load_instruments()
    assert inst["Nordnet Suomi Indeksi"].ticker == "^OMXH25"
    assert inst["Nordnet Suomi Indeksi"].note
    assert inst["Microsoft"].currency == "USD" and inst["Microsoft"].tech


def test_example_holdings():
    h = load_holdings("config/holdings.example.toml")
    assert isinstance(h.as_of, date)
    assert [p.ticker for p in h.positions] == ["MSFT", "^OMXH25"]
    assert h.positions[0].value_eur == 1800.0
    assert h.cash_eur == 250.0


def test_gitignore_hides_private():
    text = Path(".gitignore").read_text()
    for entry in ("config/*.local.toml", "data/", "out/"):
        assert entry in text


def test_tech_list():
    from nordic_desk.config import load_tech
    assert set(load_tech()) == {"AAPL", "MSFT", "NVDA", "AVGO", "ORCL"}


def test_instrument_holdings_from(tmp_path):
    p = tmp_path / "inst.toml"
    p.write_text('["Fund A"]\nticker = "FUNDA.DE"\ncurrency = "EUR"\nholdings_from = "XLK"\n\n'
                 '["Stock B"]\nticker = "B"\ncurrency = "USD"\n', encoding="utf-8")
    inst = load_instruments(p)
    assert inst["Fund A"].holdings_from == "XLK"
    assert inst["Stock B"].holdings_from == ""
