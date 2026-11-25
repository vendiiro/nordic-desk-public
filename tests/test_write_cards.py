import json

import numpy as np
import pandas as pd

from nordic_desk import prices
from nordic_desk.cards import write_cards

END = "2026-01-14"
IDX = pd.bdate_range("2023-06-01", END)


def fake_update(tickers, root, **kw):
    for t in tickers:
        if t == "BAD":
            continue
        v = np.full(len(IDX), 1.1) if t == "EURUSD=X" else 100 * np.cumprod(1 + np.random.default_rng(len(t)).normal(0, 0.01, len(IDX)))
        prices.update([t], root=root, fetch=lambda tk, s, v=v: pd.Series(v, index=IDX))
    return {t: "ok" for t in tickers}


def fake_data(t):
    if t == "BAD":
        raise RuntimeError("no such ticker")
    return {"ticker": t, "name": t, "sector": "Healthcare", "industry": "x", "currency": "USD", "quote_type": "EQUITY",
            "market_cap": 5e9, "target_mean": 150.0, "target_low": 100.0, "target_high": 200.0, "n_analysts": 12,
            "rating_counts": {"buy": 6, "hold": 6}, "results": []}


def test_write_cards_merges_and_reports_errors(tmp_path):
    out = tmp_path / "out"
    kw = dict(out_dir=out, price_root=tmp_path / "p", holdings_path="config/holdings.example.toml", end=END,
              update=fake_update, get_data=fake_data)
    first = write_cards(["LLY", "BAD"], "searched", **kw)
    write_cards(["PG"], "diversify", **kw)
    d = json.loads((out / "cards.json").read_text(encoding="utf-8"))
    assert set(d["cards"]) == {"LLY", "PG"}
    assert d["groups"] == {"searched": ["LLY"], "diversify": ["PG"]}
    assert "BAD" in first["errors"] and "no such ticker" in first["errors"]["BAD"]
    assert d["cards"]["LLY"]["impact"] is not None


def test_failed_search_not_persisted(tmp_path):
    out = tmp_path / "out"
    kw = dict(out_dir=out, price_root=tmp_path / "p", holdings_path="config/holdings.example.toml", end=END,
              update=fake_update, get_data=fake_data)
    doc = write_cards(["BAD"], "searched", **kw)
    assert "BAD" in doc["errors"]
    assert "BAD" not in json.loads((out / "cards.json").read_text(encoding="utf-8"))["errors"]


def test_history_and_alerts_across_runs(tmp_path):
    out = tmp_path / "out"
    targets = iter([105.0, 1000.0])          # second run: target far above price, so below the buy threshold

    def data(t):
        d = fake_data(t)
        if t == "LLY":                       # holdings are fetched too; only the candidate's target changes
            d["target_mean"] = next(targets)
        return d
    kw = dict(out_dir=out, price_root=tmp_path / "p", holdings_path="config/holdings.example.toml", update=fake_update, get_data=data)
    write_cards(["LLY"], "searched", end="2026-01-13", **kw)
    doc = write_cards(["LLY"], "searched", end=END, **kw)
    h = doc["cards"]["LLY"]["history"]
    assert h["since"] == "2026-01-13" and h["target"] > 5
    assert [a["ticker"] for a in doc["alerts"]] == ["LLY"]
    assert json.loads((out / "alerts.json").read_text(encoding="utf-8"))[0]["now"] == "below buy threshold"


def test_search_keeps_alerts_and_failed_ticker_drops_its_own(tmp_path):
    out = tmp_path / "out"
    targets = {"LLY": iter([105.0, 1000.0])}

    def data(t):
        if t == "BAD":
            raise RuntimeError("down")
        d = fake_data(t)
        if t in targets:
            d["target_mean"] = next(targets[t])
        return d
    kw = dict(out_dir=out, price_root=tmp_path / "p", holdings_path="config/holdings.example.toml", update=fake_update, get_data=data)
    write_cards(["LLY"], "diversify", end="2026-01-13", **kw)
    write_cards(["LLY"], "diversify", end=END, **kw)                    # LLY crosses: alert
    write_cards(["PG"], "searched", end=END, **kw)                      # a search must not wipe it
    saved = json.loads((out / "alerts.json").read_text(encoding="utf-8"))
    assert [a["ticker"] for a in saved] == ["LLY"]
    targets["LLY"] = iter([])                                           # now LLY fails: its stale alert goes
    write_cards(["LLY"], "diversify", end=END, get_data=lambda t: (_ for _ in ()).throw(RuntimeError("down")),
                **{k: v for k, v in kw.items() if k != "get_data"})
    assert json.loads((out / "alerts.json").read_text(encoding="utf-8")) == []


def test_fund_fetch_failure_does_not_stop_card(tmp_path):
    def get_fund(t):
        raise RuntimeError("yahoo down")
    out = tmp_path / "out"
    doc = write_cards(["LLY"], "searched", out_dir=out, price_root=tmp_path / "p", holdings_path="config/holdings.example.toml",
                      end=END, update=fake_update, get_data=fake_data, get_fund=get_fund)
    lt = doc["cards"]["LLY"]["lookthrough"]
    assert set(lt["no_data"]) == {"MSFT", "^OMXH25"}
    assert doc["meta"]["default_amount"] in (1000, 2000, 3000, 5000)


def test_saved_brief_attached(tmp_path):
    b = {"ticker": "LLY", "articles": [], "for": [], "against": []}
    f = tmp_path / "news" / "briefs" / "LLY.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps(b), encoding="utf-8")
    doc = write_cards(["LLY"], "searched", out_dir=tmp_path / "out", price_root=tmp_path / "p",
                      holdings_path="config/holdings.example.toml", end=END, update=fake_update, get_data=fake_data)
    assert doc["cards"]["LLY"]["brief"] == b
