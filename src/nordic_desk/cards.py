"""Candidate card: price and results, analyst signals and the before-and-after effect on the portfolio.

Prices, targets and thresholds stay in the listing currency; risk and expected return are in euros
(spec: docs/superpowers/specs/2026-11-18-search-and-signals-design.md).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import prices
from .config import load_holdings, load_instruments, load_tech
from .panel import eur_panel
from .risk import add_scenario, asset_view, portfolio_stats
from .signals import implied_return, load_signal_config, rating_share, size_label, status, thresholds

AMOUNTS = (500, 1000, 2500, 5000)  # fallback when config/target.toml has no card_amounts
DEFAULT_AMOUNT = 1000
YEARS_DAYS = 5 * 252
MARKET, FX = "SPY", "EURUSD=X"
SUBUNITS = {"GBp": ("GBP", 100.0), "GBX": ("GBP", 100.0), "ILA": ("ILS", 100.0), "ZAc": ("ZAR", 100.0)}  # quoted in pence, agorot, cents


def load_card_amounts(target_path: str | Path = "config/target.toml") -> tuple[tuple[int, ...], int]:
    """Amounts of new money shown on each card (ascending) and the one selected by default."""
    import tomllib

    with open(target_path, "rb") as f:
        d = tomllib.load(f)
    if "card_amounts" not in d:
        return AMOUNTS, DEFAULT_AMOUNT
    amounts = tuple(sorted(int(a) for a in d["card_amounts"]))
    default = int(d.get("card_default", amounts[0]))
    if default not in amounts:
        raise ValueError(f"card_default {default} is not one of card_amounts {list(amounts)}")
    return amounts, default


def _lookthrough_block(ticker: str, name: str, values: dict[str, float], cash: float, funds: dict, cand_fund: dict | None,
                       amounts: tuple[int, ...]) -> dict:
    """Portfolio share per focus company, funds looked through, now and after each amount."""
    from .lookthrough import company_key, look_through, share_after

    base = look_through(values, cash, funds)
    after = {str(a): share_after(values, cash, funds, ticker, a, cand_fund) for a in amounts}
    share = lambda lt, k: lt["companies"][k]["share"] if k in lt["companies"] else 0.0
    if cand_fund is None:
        focus, names = [company_key(ticker)], {company_key(ticker): name}
    else:  # a fund: the three companies it adds most money to (an already large holding's share can still fall)
        big = after[str(max(amounts))]
        added = lambda k: big["companies"][k]["value"] - (base["companies"][k]["value"] if k in base["companies"] else 0.0)
        focus = [k for k in sorted(big["companies"], key=added, reverse=True)[:3] if added(k) > 0]
        names = {k: big["companies"][k]["name"] for k in focus}
    pick = lambda lt: {k: round(share(lt, k), 4) for k in focus}
    via = {k: round(base["companies"][k]["via_funds"] / base["total"], 4) if k in base["companies"] and base["total"] else 0.0
           for k in focus}
    return {"focus": focus, "names": names, "before": pick(base), "via_funds": via, "amounts": {a: pick(lt) for a, lt in after.items()},
            "not_broken_down": round(base["not_broken_down"] / base["total"], 4) if base["total"] else 0.0,
            "no_data": base["no_data"]}


def fx_unit(ccy: str) -> tuple[str, float]:
    """Currency whose EUR rate to use, and the divisor that turns the quote into that currency."""
    return SUBUNITS.get(ccy, (ccy, 1.0))


def _cut(s: pd.Series, end: str) -> pd.Series:
    return s[s.index <= pd.Timestamp(end)]


def _price_block(close: pd.Series, spy: pd.Series) -> dict:
    c = close.iloc[-(YEARS_DAYS + 1):]
    sp = spy.reindex(c.index).ffill().bfill()
    peak = c.cummax()
    return {"dates": [d.strftime("%Y-%m-%d") for d in c.index], "close": c.tolist(),
            "spy_scaled": (sp / sp.iloc[0] * c.iloc[0]).tolist(),
            "ret": float(c.iloc[-1] / c.iloc[0] - 1), "worst_fall": float((c / peak - 1).min())}


def _analyst_block(data: dict, last: float, cfg: dict) -> dict:
    tm = data.get("target_mean")
    buy, sell = thresholds(tm, cfg["buy_margin"]) if tm else (None, None)
    return {"count": data.get("n_analysts") or 0, "rating_share": rating_share(data.get("rating_counts") or {}),
            "target_mean": tm, "target_low": data.get("target_low"), "target_high": data.get("target_high"),
            "upside": (tm / last - 1) if tm else None, "buy_below": buy, "sell_above": sell,
            "status": status(last, buy, sell, data.get("n_analysts") or 0, cfg["thin_coverage"])}


def build_card(ticker: str, data: dict, holdings_path: str = "config/holdings.local.toml", price_root: Path = prices.ROOT,
               end: str | None = None, analysts: dict[str, dict] | None = None, funds: dict[str, dict | None] | None = None,
               cand_fund: dict | None = None, amounts: tuple[int, ...] = AMOUNTS) -> dict:
    cfg = load_signal_config()
    load = lambda t: prices.load(t, root=price_root)
    spy_usd = load(MARKET)
    end = end or spy_usd.index[-1].strftime("%Y-%m-%d")
    close = _cut(load(ticker), end)
    card = {"ticker": ticker, "name": data.get("name") or ticker, "sector": data.get("sector"), "industry": data.get("industry"),
            "currency": data.get("currency"), "type": data.get("quote_type"), "size": size_label(data.get("market_cap")),
            "market_cap": data.get("market_cap"), "results": data.get("results") or [], "price": None,
            "analysts": None, "impact": None, "impact_note": "", "price_note": "", "lookthrough": None}
    if close.empty:
        card["impact_note"] = "no prices from Yahoo"
        return card
    if len(close) >= 253:
        card["price"] = _price_block(close, _cut(spy_usd, end))
    else:
        card["price_note"] = "not enough price history for a chart (under one year)"
    card["analysts"] = _analyst_block(data, float(close.iloc[-1]), cfg)

    # ---- portfolio before and after, in euros ----
    ccy_c, div = fx_unit(data.get("currency") or "USD")
    rates = {}
    if ccy_c not in ("USD", "EUR"):
        r = _cut(load(f"EUR{ccy_c}=X"), end)
        if r.empty:
            card["impact_note"] = f"no EUR{ccy_c} exchange rate stored"
            return card
        rates[ccy_c] = r
    h = load_holdings(holdings_path)
    inst = load_instruments()
    cur = {i.ticker: i.currency for i in inst.values()}
    tech = {i.ticker for i in inst.values() if i.tech} | set(load_tech())
    values: dict[str, float] = {}
    for p in h.positions:
        if p.ticker:
            values[p.ticker] = values.get(p.ticker, 0.0) + p.value_eur
    cash = h.cash_eur + sum(p.value_eur for p in h.positions if not p.ticker)
    tickers = list(dict.fromkeys(list(values) + [ticker, MARKET]))
    ccy = {t: cur.get(t, "USD") for t in tickers} | {ticker: ccy_c, MARKET: "USD"}
    try:
        series = {t: _cut(load(t), end) / (div if t == ticker else 1.0) for t in tickers}
        panel = eur_panel(series, ccy, _cut(load(FX), end), end, rates=rates)
    except ValueError as e:
        card["impact_note"] = (f"portfolio comparison not available: {e}" if "rate" in str(e)
                               else "not enough price history for the portfolio comparison")
        return card
    cand_tech = tech | ({ticker} if data.get("sector") == "Technology" else set())
    base = portfolio_stats(panel, values, cash, tech)
    view = asset_view(panel, ticker, base)
    ups = {t: (analysts or {}).get(t, {}).get("upside") for t in values}
    ups[ticker] = card["analysts"]["upside"]
    exp = lambda w: dict(zip(("value", "covered"), implied_return(w, ups)))
    amounts_out = {}
    for a in amounts:
        s = add_scenario(panel, values, cash, cand_tech, ticker, a)
        amounts_out[str(a)] = {k: s[k] for k in ("vol", "beta", "worst", "enb", "tech")} | {"expected": exp(s["weights"]), "own_risk": s["own_risk"]}
    card["impact"] = {"corr": view["corr"], "down": view["down"],
                      "before": {k: getattr(base, k) for k in ("vol", "beta", "worst", "enb")} | {"tech": base.tech},
                      "expected_before": exp(base.weights), "amounts": amounts_out}
    if funds is not None:
        card["lookthrough"] = _lookthrough_block(ticker, card["name"], values, cash, funds, cand_fund, amounts)
    return card


def holding_upsides(h_path: str, price_root: Path, end: str, get_data) -> dict[str, dict]:
    """Analyst upside for each held stock, in its own currency. Funds and failures give no estimate."""
    out = {}
    for p in load_holdings(h_path).positions:
        if not p.ticker or p.ticker in out:
            continue
        try:
            d = get_data(p.ticker)
        except Exception:
            continue
        close = _cut(prices.load(p.ticker, root=price_root), end)
        if d.get("target_mean") and not close.empty:
            out[p.ticker] = {"upside": d["target_mean"] / float(close.iloc[-1]) - 1}
    return out


def write_cards(tickers: list[str], group: str, out_dir: Path = Path("out"), price_root: Path = prices.ROOT,
                holdings_path: str = "config/holdings.local.toml", end: str | None = None,
                update=prices.update, get_data=None, get_fund=None, target_path: str = "config/target.toml") -> dict:
    """Fetch, build and merge cards for `tickers` under `group` into out/cards.json. Failing tickers go to `errors`."""
    import json
    from datetime import datetime, timezone

    from .candidates import load_or_fetch
    from .history import alerts, append_snapshot, change_since, previous

    from .brief import load_brief
    from .lookthrough import fund_holdings, resolve_funds

    get_data = get_data or load_or_fetch
    get_fund = get_fund or (lambda t: fund_holdings(t, cache_dir=Path(price_root).parent / "funds"))  # data/funds next to the price store
    amounts, default_amount = load_card_amounts(target_path)
    held = list(dict.fromkeys(p.ticker for p in load_holdings(holdings_path).positions if p.ticker))
    update(list(dict.fromkeys(tickers + held + [MARKET, FX])), root=price_root)
    from .build import last_full_close  # a bar dated today may still be the open session
    end = end or last_full_close(prices.load(MARKET, root=price_root))
    path = Path(out_dir) / "cards.json"
    doc = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"cards": {}, "groups": {}, "errors": {}}
    ups = holding_upsides(holdings_path, price_root, end, get_data)
    stand_in = {i.ticker: i.holdings_from for i in load_instruments().values() if i.holdings_from}
    funds = resolve_funds(held, get_fund, stand_in)
    hpath = Path(price_root).parent / "analysts_history.csv"  # data/analysts_history.csv next to the price store
    failed = {}
    for t in tickers:
        try:
            data = get_data(t)
            base_ccy = fx_unit(data.get("currency") or "USD")[0]
            if base_ccy not in ("USD", "EUR"):
                update([f"EUR{base_ccy}=X"], root=price_root)
            cand_fund = None
            if data.get("quote_type") == "ETF":
                cand_fund = resolve_funds([t], get_fund, {})[t] or {"ticker": t, "holdings": [], "covered": 0.0, "no_data": True}
            card = build_card(t, data, holdings_path, price_root, end, ups, funds=funds, cand_fund=cand_fund, amounts=amounts)
            card["history"] = change_since(card, previous(t, end, hpath))
            card["brief"] = load_brief(t, Path(price_root).parent / "news")  # data/news next to the price store
            append_snapshot(card, end, hpath)
        except Exception as e:
            failed[t] = str(e)
            continue
        doc["errors"].pop(t, None)
        doc["cards"][t] = card
        g = doc["groups"].setdefault(group, [])
        if t not in g:
            g.append(t)
    done = [t for t in tickers if t not in failed and t in doc["cards"]]
    kept = [a for a in doc.get("alerts", []) if a["ticker"] not in tickers]  # other runs' alerts stay
    doc["alerts"] = kept + alerts({t: doc["cards"][t] for t in done})
    (Path(out_dir)).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "alerts.json").write_text(json.dumps(doc["alerts"], ensure_ascii=False), encoding="utf-8")
    doc["meta"] = {"close": end, "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "default_amount": default_amount}
    path.parent.mkdir(parents=True, exist_ok=True)
    if group != "searched":  # a mistyped search is not worth keeping on the page
        doc["errors"].update(failed)
    path.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return {**doc, "errors": {**doc["errors"], **failed}}
