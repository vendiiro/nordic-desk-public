import pytest

from nordic_desk import candidates as c

HITS = [{"symbol": "NOK", "shortname": "Nokia Corporation", "exchange": "NYQ", "quoteType": "EQUITY"},
        {"symbol": "NOKIA.HE", "shortname": "Nokia Oyj", "exchange": "HEL", "quoteType": "EQUITY"},
        {"symbol": "NRE.HA", "shortname": "Nokia", "exchange": "HAN", "quoteType": "EQUITY"},
        {"symbol": "NOKOPT", "shortname": "Nokia option", "exchange": "NYQ", "quoteType": "OPTION"}]

INFO = {"shortName": "Eli Lilly and Company", "sector": "Healthcare", "industry": "Drug Manufacturers", "currency": "USD",
        "quoteType": "EQUITY", "marketCap": 1.3e12, "targetMeanPrice": 1200.0, "targetLowPrice": 900.0, "targetHighPrice": 1500.0,
        "numberOfAnalystOpinions": 25}
RECS = {"strongBuy": 5, "buy": 20, "hold": 4, "sell": 1, "strongSell": 1}
FIN = [{"year": 2025, "revenue": 60e9, "net_income": 20e9}, {"year": 2024, "revenue": 45e9, "net_income": 10e9}]


def fetchers(calls=None):
    def info(t):
        if calls is not None:
            calls.append(t)
        return dict(INFO)
    return {"fetch_info": info, "fetch_recs": lambda t: dict(RECS), "fetch_fin": lambda t: list(FIN)}


def test_search_filters_exchange_and_type():
    hits = c.search("nokia", fetch=lambda text: HITS)
    assert [h["symbol"] for h in hits] == ["NOK", "NOKIA.HE"]
    assert hits[1] == {"symbol": "NOKIA.HE", "name": "Nokia Oyj", "exchange": "HEL", "type": "EQUITY"}


def test_fetch_candidate_fields():
    d = c.fetch_candidate("LLY", **fetchers())
    assert d["name"] == "Eli Lilly and Company" and d["n_analysts"] == 25 and d["target_mean"] == 1200.0
    assert d["rating_counts"] == RECS and d["results"][0]["year"] == 2025


def test_etf_has_no_results():
    f = fetchers()
    f["fetch_info"] = lambda t: {**INFO, "quoteType": "ETF"}
    assert c.fetch_candidate("XLV", **f)["results"] == []


def test_cache_hit_skips_fetch(tmp_path):
    calls = []
    c.load_or_fetch("LLY", cache_dir=tmp_path, **fetchers(calls))
    c.load_or_fetch("LLY", cache_dir=tmp_path, **fetchers(calls))
    assert calls == ["LLY"]


def test_fetch_error_is_named(tmp_path):
    f = fetchers()
    f["fetch_info"] = lambda t: (_ for _ in ()).throw(RuntimeError("down"))
    with pytest.raises(c.CandidateError, match="ZZZ"):
        c.load_or_fetch("ZZZ", cache_dir=tmp_path, **f)
