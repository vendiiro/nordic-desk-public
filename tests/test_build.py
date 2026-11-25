import json
import math
import re
from pathlib import Path

import numpy as np
import pytest
import pandas as pd

from nordic_desk import prices
from nordic_desk.build import build

WATCH = ["AAPL", "MSFT", "XOM"]


def fill_store(root: Path):
    rng = np.random.default_rng(7)
    idx = pd.bdate_range("2024-06-03", "2026-01-14")
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0004, 0.015, len(idx))) for t in WATCH + ["SPY", "^OMXH25"]}
    data["EURUSD=X"] = 1.1 + 0.01 * np.sin(np.arange(len(idx)) / 20)
    for t, v in data.items():
        prices.update([t], root=root, fetch=lambda tk, start, v=v: pd.Series(v, index=idx))


def contract_keys(section: str) -> set[str]:
    text = Path("docs/data-contract.md").read_text(encoding="utf-8")
    block = text.split(f"## {section}")[1].split("\n## ")[0]
    return set(re.findall(r"^- `([a-z_0-9]+)`", block, flags=re.M))


def all_numbers(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from all_numbers(v)
    elif isinstance(x, list):
        for v in x:
            yield from all_numbers(v)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield x


def test_build_offline(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    out = tmp_path / "out"
    build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml",
          watchlist=WATCH, out_dir=out)
    desk = json.loads((out / "desk.json").read_text(encoding="utf-8"))
    aamu = json.loads((out / "aamu.json").read_text(encoding="utf-8"))
    assert set(desk) == contract_keys("desk.json")
    assert set(aamu) == contract_keys("aamu.json")
    assert all(math.isfinite(v) for v in all_numbers(desk))
    assert all(math.isfinite(v) for v in all_numbers(aamu))
    held = {r["ticker"]: r["held"] for r in desk["watchlist"]}
    assert held == {"AAPL": False, "MSFT": True, "XOM": False}
    ids = {s["id"] for s in desk["impact"]["scenarios"]}
    assert {"add-AAPL-1000", "add-SPY-5000", "sell-MSFT", "sell-^OMXH25"} <= ids
    assert "add-MSFT-1000" not in ids
    assert abs(sum(h["risk"] for h in desk["impact"]["holdings"]) - 1) < 1e-9
    assert desk["record"] is None
    assert len(aamu["movers"]["up"]) <= 3 and len(aamu["tiles"]) == 3
    assert all(m["d1"] > 0 for m in aamu["movers"]["up"]) and all(m["d1"] < 0 for m in aamu["movers"]["down"])


def test_default_end_skips_today(tmp_path):
    from nordic_desk.build import last_full_close
    idx = pd.to_datetime(["2026-01-12", "2026-01-13", "2026-01-14"])
    spy = pd.Series([1.0, 2.0, 3.0], index=idx)
    assert last_full_close(spy, today=pd.Timestamp("2026-01-14")) == "2026-01-13"
    assert last_full_close(spy, today=pd.Timestamp("2026-01-15")) == "2026-01-14"


def run(tmp_path, holdings="config/holdings.example.toml", watch=WATCH):
    store = tmp_path / "prices"
    fill_store(store)
    out = tmp_path / "out"
    build(end="2026-01-14", price_root=store, holdings_path=holdings, watchlist=watch, out_dir=out)
    return json.loads((out / "desk.json").read_text(encoding="utf-8")), json.loads((out / "aamu.json").read_text(encoding="utf-8"))


def test_missing_ticker_skipped_not_fatal(tmp_path):
    desk, aamu = run(tmp_path, watch=WATCH + ["BOGUS"])
    assert desk["meta"]["skipped"] == ["BOGUS"]
    assert [r["ticker"] for r in desk["watchlist"]] == WATCH
    assert not any(s["ticker"] == "BOGUS" for s in desk["impact"]["scenarios"])


def test_duplicate_ticker_lines_summed(tmp_path):
    src = Path("config/holdings.example.toml").read_text(encoding="utf-8")
    dup = src + '\n[[position]]\nname = "Microsoft second lot"\nticker = "MSFT"\nquantity = 1\nvalue_eur = 300.0\ncost_eur = 280.0\n'
    p = tmp_path / "h.toml"
    p.write_text(dup, encoding="utf-8")
    desk, _ = run(tmp_path, holdings=str(p))
    assert desk["portfolio"]["value_report"] == 1800.0 + 300.0 + 1200.0 + 250.0
    ms = [h for h in desk["impact"]["holdings"] if h["ticker"] == "MSFT"]
    assert len(ms) == 1 and ms[0]["value"] == 2100.0


def test_since_cost_uses_position_cost(tmp_path):
    desk, aamu = run(tmp_path)
    p = desk["portfolio"]
    assert p["cost"] == 1500.0 + 1100.0
    assert aamu["portfolio"]["since_cost_pct"] == pytest.approx(p["unrealised"] / 2600.0)
    assert p["unrealised"] == pytest.approx(p["value"] - 2600.0 - 250.0)


def test_detail_has_facts(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    prices.update_info(["AAPL"], path=tmp_path / "info.json", fetch=lambda t: {"shortName": "Apple Inc.", "trailingPE": 30.0})
    out = tmp_path / "out"
    build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=out)
    desk = json.loads((out / "desk.json").read_text(encoding="utf-8"))
    assert desk["detail"]["AAPL"]["facts"]["name"] == "Apple"
    assert desk["detail"]["XOM"]["facts"] == {}


def test_report_before_prices_is_a_clear_error(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    src = Path("config/holdings.example.toml").read_text(encoding="utf-8").replace("as_of = 2026-01-15", "as_of = 2020-01-15")
    h = tmp_path / "h.toml"
    h.write_text(src, encoding="utf-8")
    with pytest.raises(ValueError, match="MSFT"):
        build(end="2026-01-14", price_root=store, holdings_path=str(h), watchlist=WATCH, out_dir=tmp_path / "out")


def test_single_holding_has_no_sell_scenario(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    src = Path("config/holdings.example.toml").read_text(encoding="utf-8")
    one = src[: src.rindex("[[position]]")]
    h = tmp_path / "one.toml"
    h.write_text(one, encoding="utf-8")
    build(end="2026-01-14", price_root=store, holdings_path=str(h), watchlist=WATCH, out_dir=tmp_path / "out")
    desk = json.loads((tmp_path / "out" / "desk.json").read_text(encoding="utf-8"))
    assert not [s for s in desk["impact"]["scenarios"] if s["kind"] == "sell"]


def test_forecast_in_desk(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=tmp_path / "out")
    f = json.loads((tmp_path / "out" / "desk.json").read_text(encoding="utf-8"))["forecast"]
    assert f["low"] < f["value"] < f["high"] and set(f["models"]) == {"ewma", "garch", "bootstrap", "regime"}
    assert f["backtest"] is None  # about 420 days of fake prices: too short to calibrate


def test_desk_lookthrough_with_fund(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    inst = tmp_path / "inst.toml"
    inst.write_text('["Microsoft"]\nticker = "MSFT"\ncurrency = "USD"\ntech = true\n\n'
                    '["Nordnet Suomi Indeksi"]\nticker = "^OMXH25"\ncurrency = "EUR"\nholdings_from = "XLK"\n', encoding="utf-8")
    xlk = {"ticker": "XLK", "covered": 0.2, "holdings": [{"symbol": "MSFT", "name": "Microsoft", "weight": 0.2}]}
    desk = build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH,
                 out_dir=tmp_path / "out", instruments_path=str(inst), get_fund=lambda t: xlk if t == "XLK" else None)
    lt = desk["lookthrough"]
    assert lt["top"][0]["key"] == "MSFT" and lt["top"][0]["via_funds"] > 0
    assert lt["no_data"] == [] and lt["not_broken_down"] == pytest.approx(1200 * 0.8 / 3250, abs=1e-4)


def test_cli_lookthrough(capsys, monkeypatch):
    from nordic_desk.build import main
    monkeypatch.setattr("nordic_desk.lookthrough.fund_holdings", lambda t, **kw: None)
    main(["lookthrough", "--holdings", "config/holdings.example.toml"])
    out = capsys.readouterr().out
    assert out.startswith("Largest companies, including funds") and "Microsoft" in out


def test_desk_staleness(tmp_path):
    import json
    from nordic_desk.build import desk_staleness
    root = tmp_path / "prices"
    idx = pd.bdate_range("2026-01-05", periods=10)
    prices.update(["SPY"], root=root, fetch=lambda t, s: pd.Series(1.0, index=idx))
    out = tmp_path / "out"
    out.mkdir()
    (out / "desk.json").write_text(json.dumps({"meta": {"close": "2026-01-16"}, "record": None}), encoding="utf-8")
    assert desk_staleness(out, root) is None  # desk built on the newest close
    (out / "desk.json").write_text(json.dumps({"meta": {"close": "2026-01-09"}, "record": None}), encoding="utf-8")
    assert desk_staleness(out, root) == ("2026-01-09", "2026-01-16")


def test_goal_json_and_ledger(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    out = tmp_path / "out"
    build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=out,
          goals_path="config/goals.example.toml")
    g = json.loads((out / "goal.json").read_text(encoding="utf-8"))
    assert g["available"] and g["drift"] == 0.07 and g["history_start"] < "2024-07-01" and g["close"] == "2026-01-14"
    assert len(g["years"]) == g["horizon_years"] == 5 and g["goal"]["target"] == 50000 and g["goal"]["years_ahead"] == 5
    assert g["backtest"] is None  # about 400 days of fake prices: too short for a one-year back-test
    assert g["anchor"]["rate"] is not None and g["ledger"]["pending"] == 3 and g["ledger"]["show"] is False
    rows = [json.loads(x) for x in (tmp_path / "ledger" / "forecasts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["kind"] for r in rows} == {"goal_1y", "goal_5y", "risk_21d"} and all(r["made"] == "2026-01-14" for r in rows)
    build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=out,
          goals_path="config/goals.example.toml")
    assert len((tmp_path / "ledger" / "forecasts.jsonl").read_text(encoding="utf-8").splitlines()) == 3  # same week: no new rows


def test_goal_without_goals_file(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    out = tmp_path / "out"
    build(end="2026-01-14", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=out)
    g = json.loads((out / "goal.json").read_text(encoding="utf-8"))
    assert g["available"] and g["goal"] is None and g["monthly"] == 0 and g["goals_file"] is False


def test_ledger_skips_a_build_on_a_past_close(tmp_path):
    store = tmp_path / "prices"
    fill_store(store)
    build(end="2026-01-09", price_root=store, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=tmp_path / "out",
          goals_path="config/goals.example.toml")
    assert not (tmp_path / "ledger" / "forecasts.jsonl").exists()  # weights are today's: a past date would be hindsight
