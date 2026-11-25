"""Command line: update prices, import the Nordnet report, build out/desk.json and out/aamu.json."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import prices
from .config import load_holdings, load_ideas, load_instruments, load_tech, load_watchlist
from .nordnet import parse_report, read_export, twr, write_holdings
from .panel import eur_panel, to_eur
from .forecast import portfolio_forecast
from .risk import add_scenario, asset_view, portfolio_stats, sell_scenario
from .stocks import rebased, stock_stats

MARKET, FX = "SPY", "EURUSD=X"
HOLDINGS = "config/holdings.local.toml"


def last_full_close(spy: pd.Series, today: pd.Timestamp | None = None) -> str:
    """Latest SPY date before today: a bar dated today may still be the open session."""
    today = (today or pd.Timestamp.now()).normalize()
    return spy.index[spy.index < today][-1].strftime("%Y-%m-%d")


def _clean(x):
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return round(float(x), 10)
    if isinstance(x, np.integer):
        return int(x)
    return x


def _dates(idx) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in idx]


def build(end: str | None = None, record: str | None = None, price_root: Path = prices.ROOT,
          holdings_path: str = HOLDINGS, watchlist: list[str] | None = None, out_dir: Path = Path("out"),
          instruments_path: str = "config/instruments.toml", get_fund=None, goals_path: str | None = None) -> dict:
    watchlist = watchlist or load_watchlist()
    inst = load_instruments(instruments_path)
    cur = {i.ticker: i.currency for i in inst.values()}
    tech = {i.ticker for i in inst.values() if i.tech} | set(load_tech())
    note = {i.ticker: i.note for i in inst.values()}
    h = load_holdings(holdings_path)

    load = lambda t: prices.load(t, root=price_root)
    spy_usd, eurusd = load(MARKET), load(FX)
    end = end or last_full_close(spy_usd)
    cut = lambda s: s[s.index <= pd.Timestamp(end)]
    spy_usd, eurusd = cut(spy_usd), cut(eurusd)
    fx_now = float(eurusd.iloc[-1])

    unmodelled = [p for p in h.positions if not p.ticker]
    values: dict[str, float] = {}
    names: dict[str, str] = {}
    for p in h.positions:
        if p.ticker:  # several report lines on one ticker are one position
            values[p.ticker] = values.get(p.ticker, 0.0) + p.value_eur
            names.setdefault(p.ticker, p.name)
    cash = h.cash_eur + sum(p.value_eur for p in unmodelled)

    def enough(t: str) -> bool:
        s = load(t)
        return len(s[s.index <= pd.Timestamp(end)]) >= 254

    no_history = [t for t in values if not enough(t)]
    if no_history:
        raise ValueError(f"not enough price history for held tickers: {', '.join(no_history)}; run `nordic-desk update`")
    skipped = [t for t in watchlist if not enough(t)]
    watchlist = [t for t in watchlist if t not in skipped]
    candidates = [t for t in watchlist if t not in values] + [MARKET]

    # ---- watchlist (USD) ----
    facts = prices.load_info(Path(price_root).parent / "info.json")
    closes = {t: cut(load(t)) for t in watchlist}
    stats = {t: stock_stats(closes[t], spy_usd) for t in watchlist}
    rows = [{"ticker": t, "held": t in values, "last_usd": s["last"], "d1": s["d1"], "w1": s["w1"], "m1": s["m1"],
             "m3": s["m3"], "m6": s["m6"], "ytd": s["ytd"], "y1": s["y1"], "hi_usd": s["hi"], "lo_usd": s["lo"],
             "pos": s["pos"], "vol": s["vol"], "mdd": s["mdd"], "beta": s["beta"],
             "spark": closes[t].iloc[-64:].tolist()} for t, s in stats.items()]
    detail = {}
    for t in watchlist:
        c = closes[t].iloc[-253:]
        sp = spy_usd.reindex(c.index).ffill()
        detail[t] = {"dates": _dates(c.index), "close_usd": c.tolist(), "spy_scaled": (sp / sp.iloc[0] * c.iloc[0]).tolist(),
                     "facts": facts.get(t, {})}
    spy_win = spy_usd.iloc[-253:]
    compare = {"dates": _dates(spy_win.index), "series": {t: rebased(closes[t]) for t in watchlist}, "spy": rebased(spy_usd),
               "spy_stats": stock_stats(spy_usd, spy_usd)}

    # ---- portfolio risk (EUR) ----
    tickers = list(dict.fromkeys(list(values) + candidates))
    series = {t: cut(load(t)) for t in tickers}
    ccy = {t: cur.get(t, "USD") for t in tickers}
    panel = eur_panel(series, ccy, eurusd, end)
    base = portfolio_stats(panel, values, cash, tech)
    eur_last = {t: to_eur(series[t], eurusd, ccy[t]) for t in values}
    early = [t for t, s in eur_last.items() if not (s.index <= pd.Timestamp(h.as_of)).any()]
    if early:
        raise ValueError(f"the report date {h.as_of} is before the first stored price of: {', '.join(early)}")
    at_report = {t: s[s.index <= pd.Timestamp(h.as_of)].iloc[-1] for t, s in eur_last.items()}
    revalued = {t: values[t] * s.iloc[-1] / at_report[t] for t, s in eur_last.items()}
    value_now = sum(revalued.values()) + cash
    cost = sum((p.cost_eur if p.cost_eur is not None else p.value_eur) for p in h.positions)  # positions only
    hist = sum(panel[t] / panel[t].iloc[-1] * revalued[t] for t in values) + cash
    spy_hist = panel[MARKET] / panel[MARKET].iloc[0] * hist.iloc[0]
    portfolio = {"value": value_now, "value_report": sum(values.values()) + cash, "cost": cost,
                 "unrealised": value_now - cost - h.cash_eur, "cash": cash,
                 **{k: getattr(base, k) for k in ("vol", "beta", "worst", "ret", "tech", "enb")},
                 "history": {"dates": _dates(panel.index), "value": hist.tolist()}, "spy_history": spy_hist.tolist()}

    hold_rows = []
    for t in values:
        v = asset_view(panel, t, base)
        hold_rows.append({"name": names[t], "ticker": t, "note": note.get(t, ""), "value": values[t],
                          "weight": base.weights[t], "risk": base.risk_share[t], "tech": t in tech,
                          **{k: v[k] for k in ("vol", "corr", "down", "ret")}})
    hold_rows.sort(key=lambda r: -r["risk"])
    cand_rows, scen = [], []
    keep = ("vol", "beta", "worst", "ret", "tech", "enb", "total")
    import tomllib

    from .cards import load_card_amounts
    target = Path("config/target.toml")
    amounts, default_amount = load_card_amounts(target) if target.exists() else ((500, 1000, 2500, 5000), 1000)
    tech_max = tomllib.loads(target.read_text(encoding="utf-8")).get("tech_max", 0.5) if target.exists() else 0.5
    for t in candidates:
        v = asset_view(panel, t, base)
        cand_rows.append({"ticker": t, **{k: v[k] for k in ("vol", "corr", "down", "ret")}})
        for a in amounts:
            s = add_scenario(panel, values, cash, tech, t, a)
            scen.append({"id": f"add-{t}-{a}", "kind": "add", "ticker": t, "amount": a, "own_risk": s["own_risk"],
                         **{k: s[k] for k in keep}})
    for t in (values if len(values) > 1 else []):  # selling the only holding leaves nothing to compare
        s = sell_scenario(panel, values, cash, tech, t)
        scen.append({"id": f"sell-{t}", "kind": "sell", "ticker": t, "name": names[t],
                     "amount": values[t], **{k: s[k] for k in keep}})
    impact = {"window": {"start": _dates(panel.index[:1])[0], "end": _dates(panel.index[-1:])[0]},
              "holdings": hold_rows, "unmodelled": [{"name": p.name, "value": p.value_eur} for p in unmodelled],
              "candidates": cand_rows, "scenarios": scen,
              "amounts": list(amounts), "default_amount": default_amount, "tech_max": tech_max}

    rec = None
    if record:
        df = read_export(record)
        tw = twr(df)
        spy_eur = to_eur(spy_usd, eurusd, "USD")
        spy_on = spy_eur.reindex(spy_eur.index.union(df["date"])).sort_index().ffill().reindex(df["date"])
        wk = np.diff(np.log(tw.to_numpy()))[-52:]
        rec = {"dates": _dates(df["date"]), "value": df["value"].tolist(), "deposits": df["deposits"].tolist(),
               "twr": tw.tolist(), "spy": (spy_on / spy_on.iloc[0]).tolist(),
               "vol_1y": float(np.std(wk, ddof=1) * math.sqrt(52))}

    meta = {"close": end, "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "holdings_as_of": h.as_of.isoformat(), "eurusd": fx_now, "source": "Yahoo Finance; Nordnet report and export",
            "skipped": skipped}
    from .forecast import EXCLUDE
    model_t = [t for t in values if t not in EXCLUDE]
    long_panel = eur_panel({t: series[t] for t in model_t}, {t: ccy[t] for t in model_t}, eurusd, end, n_returns=None) if model_t else None
    from .lookthrough import fund_holdings, portfolio_lookthrough
    get_fund = get_fund or (lambda t: fund_holdings(t, cache_dir=Path(price_root).parent / "funds"))  # data/funds next to the prices
    desk = {"meta": meta, "watchlist": rows, "detail": detail, "compare": compare, "portfolio": portfolio,
            "lookthrough": portfolio_lookthrough(holdings_path, instruments_path, get_fund),
            "impact": impact, "record": rec, "forecast": portfolio_forecast(long_panel, revalued, cash, cache_path=Path(price_root).parent / "forecast_cache.json") if model_t else None}

    # ---- goal: 1-10-year range, back-test and forecast ledger (out/goal.json) ----
    from .analysis_config import load as load_cfg
    from .expected import anchor
    from .goalrange import PATH as GOALS, Goals, build_goal, load_goals
    gcfg = load_cfg().goal
    # goals belong with the real holdings: a build on other holdings (tests, examples) reads none unless given a file
    goals = load_goals(goals_path or GOALS) if goals_path or holdings_path == HOLDINGS else Goals()

    def score_panel(ts: set[str]) -> pd.DataFrame:  # older ledger rows may name tickers no longer held
        have = {t: cut(load(t)) for t in ts}
        have = {t: s for t, s in have.items() if not s.empty and cur.get(t, "USD") in ("USD", "EUR")}
        try:
            return eur_panel(have, {t: cur.get(t, "USD") for t in have}, eurusd, end, n_returns=None) if have else long_panel
        except ValueError:
            return long_panel

    goal = (build_goal(long_panel, revalued, cash, end, goals, gcfg.drift, gcfg.n_paths, gcfg.block, desk["forecast"],
                       Path(price_root).parent / "ledger" / "forecasts.jsonl", anchor(to_eur(spy_usd, eurusd, "USD")), score_panel,
                       record=end == last_full_close(load(MARKET)))
            if model_t else {"available": False, "why": "Only the excluded test positions are held, so there is nothing to model."})

    # ---- aamu ----
    r_last = panel.pct_change().iloc[-1]
    overnight = sum(revalued[t] / (1 + r_last[t]) * r_last[t] for t in values)
    fx_r = eurusd.iloc[-1] / eurusd.iloc[-2] - 1
    usd_part = sum(revalued[t] / (1 + r_last[t]) for t in values if ccy[t] == "USD")
    by_d1 = sorted(rows, key=lambda r: r["d1"])
    mv = lambda r: {"ticker": r["ticker"], "d1": r["d1"], "last_usd": r["last_usd"]}
    aamu = {"meta": meta,
            "portfolio": {"value": value_now, "overnight": overnight, "overnight_pct": overnight / (value_now - overnight),
                          "since_cost_pct": portfolio["unrealised"] / portfolio["cost"] if portfolio["cost"] else 0.0,
                          "fx_effect_1d": usd_part * (1 / (1 + fx_r) - 1)},
            "spy_overnight": float(r_last[MARKET]),
            "movers": {"up": [mv(r) for r in by_d1[::-1] if r["d1"] > 0][:3], "down": [mv(r) for r in by_d1 if r["d1"] < 0][:3]},
            "tiles": [{"ticker": r["ticker"], "last_usd": r["last_usd"], "y1": r["y1"], "rebased": rebased(closes[r["ticker"]])}
                      for r in rows]}

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("desk.json", desk), ("aamu.json", aamu), ("goal.json", goal)):
        (out_dir / name).write_text(json.dumps(_clean(data), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return desk


def desk_staleness(out_dir: Path = Path("out"), price_root: Path = prices.ROOT) -> tuple[str, str] | None:
    """(desk close, newest stored close) when out/desk.json was built on older prices than the store holds, else None."""
    f = Path(out_dir) / "desk.json"
    spy = prices.load(MARKET, price_root)
    if not f.exists() or spy.empty:
        return None
    built = json.loads(f.read_text(encoding="utf-8"))["meta"]["close"]
    newest = spy.index[-1].strftime("%Y-%m-%d")
    return (built, newest) if built < newest else None


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="nordic-desk")
    sub = ap.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("update", help="fetch missing daily closes from Yahoo")
    up.add_argument("--start", default=prices.DEFAULT_START)
    imp = sub.add_parser("import-report", help="read a Nordnet portfolio report PDF into config/holdings.local.toml")
    imp.add_argument("pdf")
    b = sub.add_parser("build", help="write out/desk.json and out/aamu.json")
    b.add_argument("--record", help="Nordnet daily-development export (CSV)")
    b.add_argument("--end", help="last close to use, YYYY-MM-DD")
    hv = sub.add_parser("holdings", help="write out/holdings.html: current holdings and weights only")
    hv.add_argument("--end", help="last close to use, YYYY-MM-DD")
    sub.add_parser("site", help="write out/site/*.html from out/desk.json and out/aamu.json, plus the analysis pages")
    se = sub.add_parser("search", help="find stocks and ETFs by ticker or name")
    se.add_argument("text", nargs="+")
    ca = sub.add_parser("card", help="add candidate cards for tickers to out/cards.json")
    ca.add_argument("tickers", nargs="+")
    sub.add_parser("ideas", help="build candidate cards for every ticker in config/ideas.toml")
    pl = sub.add_parser("plan", help="split new money over the ideas, lowest volatility first")
    pl.add_argument("--amount", type=float)
    sub.add_parser("alerts", help="list stocks that crossed a buy or sell threshold in the last card run")
    br = sub.add_parser("brief", help="write an AI news brief for candidate tickers (needs a Claude key)")
    br.add_argument("tickers", nargs="+")
    lt = sub.add_parser("lookthrough", help="largest companies in the portfolio with funds looked through")
    lt.add_argument("--holdings", default=HOLDINGS, help=argparse.SUPPRESS)
    sv = sub.add_parser("serve", help="serve out/site on 127.0.0.1 with search")
    sv.add_argument("--port", type=int, default=8765)
    sv.add_argument("--lan", action="store_true", help="also serve on the home network, behind a one-time key")
    a = ap.parse_args(argv)

    if a.cmd == "plan":
        import tomllib
        from .plan import run_plan
        ideas = [t for ts in load_ideas().values() for t in ts]
        cache = Path("data/candidates")
        info = {t: json.loads((cache / f"{t}.json").read_text(encoding="utf-8")) for t in ideas if (cache / f"{t}.json").exists()}
        with open("config/target.toml", "rb") as f:
            amount = a.amount or tomllib.load(f)["amount"]
        p = run_plan(amount, ideas, info)
        for t, v in sorted(p["split"].items(), key=lambda kv: -kv[1]):
            print(f"{t:10} {v:>8,.0f} EUR")
        print(f"volatility {p['before']['vol']:.1%} -> {p['after']['vol']:.1%}, technology {p['before']['tech']:.1%} -> {p['after']['tech']:.1%}")
        if p["note"]:
            print(p["note"])
        o = p.get("optimised")
        if o:
            print("optimiser (SLSQP): " + ", ".join(f"{t} {v:,.0f}" for t, v in sorted(o["split"].items(), key=lambda kv: -kv[1]))
                  + f"; volatility {o['after']['vol']:.1%}, technology {o['after']['tech']:.1%}")
        return
    if a.cmd == "alerts":
        f = Path("out") / "alerts.json"
        items = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
        for x in items:
            print(f"{x['ticker']:10} {x['now']} (was {x.get('before') or 'not recorded'})  {x['name']}")
        if not items:
            print("No thresholds crossed since the previous card run.")
        return
    if a.cmd == "brief":
        from .brief import BriefError, load_cfg, make_brief, new_client
        from .candidates import load_or_fetch
        try:
            client = new_client()
        except BriefError as e:
            print(e)
            return
        held = {p.ticker for p in load_holdings(HOLDINGS).positions if p.ticker} if Path(HOLDINGS).exists() else set()
        cfg, path = load_cfg(), Path("out") / "cards.json"
        doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        for t in (x.upper() for x in a.tickers):
            try:
                if t in held:  # checked before any request for this ticker
                    raise BriefError(f"{t} is held: briefs are only for candidates, so your holdings never leave this computer")
                b = make_brief(t, load_or_fetch(t)["name"], cfg, held, client=client)
            except Exception as e:  # one failing ticker must not stop the others or the cards.json update
                print(f"{t}: {e}")
                continue
            print(f"{t}: {len(b['articles'])} articles, {len(b['for'])} for, {len(b['against'])} against, cost ${b['cost_usd']:.3f}")
            if doc and t in doc["cards"]:
                doc["cards"][t]["brief"] = b
        if doc:
            path.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            from .views.site import write_site
            write_site()
        return
    if a.cmd == "lookthrough":
        from . import lookthrough as L
        print(L.format_top(L.portfolio_lookthrough(a.holdings, "config/instruments.toml", lambda t: L.fund_holdings(t))))
        return
    if a.cmd == "serve":
        from .server import serve
        serve(port=a.port, lan=a.lan)
        return

    if a.cmd == "search":
        from .candidates import search
        for h in search(" ".join(a.text)):
            print(f"{h['symbol']:12} {h['exchange']:4} {h['type']:6} {h['name']}")
        return
    if a.cmd in ("card", "ideas"):
        from .cards import write_cards
        jobs = [(a.tickers, "searched")] if a.cmd == "card" else [(t, g) for g, t in load_ideas().items()]
        for tickers, group in jobs:
            doc = write_cards([t.upper() for t in tickers], group)
            print(f"{group}: {len([t for t in tickers if t.upper() in doc['cards']])} cards")
        for t, e in doc["errors"].items():
            print(f"skipped {t}: {e}")
        return

    if a.cmd == "site":
        from .views.site import write_site
        stale = desk_staleness()
        if stale and json.loads(Path("out/desk.json").read_text(encoding="utf-8")).get("record"):
            print(f"WARNING: Desk numbers are from {stale[0]} but prices go to {stale[1]}; run `nordic-desk build --record <export.csv>` first.")
        elif stale:  # Desk, Impact and Aamu read out/desk.json: rebuild it so every page shows the same close
            print(f"Desk numbers were from {stale[0]}; rebuilding them on prices to {stale[1]}.")
            build()
        for f in write_site():
            print(f"Wrote {f.resolve()}")
        return
    if a.cmd == "holdings":
        from .holdings_view import current_weights, render
        end = a.end or last_full_close(prices.load(MARKET))
        rows = current_weights(end=end)
        out = Path("out") / "holdings.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(rows, close=end, report=load_holdings(HOLDINGS).as_of.isoformat()), encoding="utf-8")
        print(f"Wrote {out.resolve()}")
        return

    if a.cmd == "update":
        tickers = load_watchlist() + [MARKET, FX]
        if Path(HOLDINGS).exists():
            tickers += [p.ticker for p in load_holdings(HOLDINGS).positions if p.ticker]
        for t, s in prices.update(list(dict.fromkeys(tickers)), start=a.start).items():
            print(f"{t:10} {s}")
        bad = {t: s for t, s in prices.update_info(load_watchlist()).items() if s != "ok"}
        print("company facts:", "ok" if not bad else bad)
        from .forecast import EXCLUDE
        from .ohlc import update_ohlc
        ideas = [t for ts in load_ideas().values() for t in ts]
        if Path("out/cards.json").exists():  # searched cards (nordic-desk card) get analysis pages too
            ideas += list(json.loads(Path("out/cards.json").read_text(encoding="utf-8")).get("cards", {}))
        pages = [t for t in dict.fromkeys(tickers + ideas) if t not in (*EXCLUDE, MARKET, FX)]  # tickers that get an analysis page
        bad = {t: s for t, s in update_ohlc(pages, start=a.start).items() if s != "ok" and not s.startswith("no new")}
        print("daily open/high/low:", "ok" if not bad else bad)
        from .fundamentals import update_fundamentals
        bad = {t: s for t, s in update_fundamentals(pages).items() if s != "ok"}
        print("fundamentals:", "ok" if not bad else bad)
    elif a.cmd == "import-report":
        h = parse_report(a.pdf, load_instruments())
        for p in h.positions:
            print(f"{p.ticker or 'UNMAPPED':10} {p.value_eur:>12,.2f}  {p.name}")
        print(f"{'cash':10} {h.cash_eur:>12,.2f}")
        missing = [p.name for p in h.positions if not p.ticker]
        if missing:
            print("Unmapped (counted as zero return; add to config/instruments.toml to model them):", "; ".join(missing))
        write_holdings(h)
        print(f"Wrote {HOLDINGS} (as of {h.as_of}).")
    else:
        desk = build(end=a.end, record=a.record)
        p = desk["portfolio"]
        print(f"close {desk['meta']['close']}: value {p['value']:,.0f} EUR, vol {p['vol']:.2%}, beta {p['beta']:.3f}, "
              f"effective holdings {p['enb']:.2f}, technology {p['tech']:.1%}")
        if desk["record"]:
            print(f"record: time-weighted {desk['record']['twr'][-1] - 1:+.2%}, weekly vol {desk['record']['vol_1y']:.2%}")
