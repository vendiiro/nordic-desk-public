import json

from nordic_desk import prices


def test_update_info_writes_and_merges(tmp_path):
    path = tmp_path / "info.json"
    fake = {"AAPL": {"shortName": "Apple Inc.", "sector": "Technology", "trailingPE": 30.5, "marketCap": 3e12,
                     "earningsTimestamp": 1767225600}}
    status = prices.update_info(["AAPL", "NOPE"], path=path, fetch=lambda t: fake.get(t, {}))
    assert status == {"AAPL": "ok", "NOPE": "empty"}
    info = prices.load_info(path)
    assert info["AAPL"]["name"] == "Apple"
    assert info["AAPL"]["pe_trailing"] == 30.5 and info["AAPL"]["pe_forward"] is None
    assert info["AAPL"]["earnings"] == "2026-01-01"
    prices.update_info(["MSFT"], path=path, fetch=lambda t: {"shortName": "Microsoft Corporation"})
    assert set(prices.load_info(path)) == {"AAPL", "MSFT"}
    assert prices.load_info(path)["MSFT"]["name"] == "Microsoft"


def test_load_info_missing_file(tmp_path):
    assert prices.load_info(tmp_path / "none.json") == {}
