"""Fund look-through: euros and portfolio share per company, direct holdings plus each fund's published top holdings.

Fund holdings come from Yahoo (`Ticker.funds_data.top_holdings`, top 10 only) and are cached daily under data/funds/.
Money outside a fund's published list is "not broken down", never guessed
(spec: docs/superpowers/specs/2026-11-20-idea-discovery-design.md, goal 1).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

CACHE = Path("data/funds")
# Listings and share classes known to be one company. Only these are joined: cutting the suffix in general would
# merge different companies (ROP.SW is Roche, ROP is Roper Technologies). An unknown cross-listing shows as its own row.
SAME_COMPANY = {"GOOG": "GOOGL", "ASML.AS": "ASML", "SAP.DE": "SAP", "NOVO-B.CO": "NVO", "AZN.L": "AZN", "SHEL.L": "SHEL",
                "TTE.PA": "TTE", "NOKIA.HE": "NOKIA.HE", "NOK": "NOKIA.HE"}


def company_key(symbol: str) -> str:
    return SAME_COMPANY.get(symbol, symbol)


def yf_top_holdings(ticker: str, ticker_cls=None) -> list[dict]:
    """Top holdings of a fund; [] for a fund Yahoo publishes none for; LookupError when the ticker is not a fund."""
    if ticker_cls is None:
        import yfinance as yf
        ticker_cls = yf.Ticker
    tk = ticker_cls(ticker)
    try:
        th = tk.funds_data.top_holdings
    except Exception as e:
        if "No Fund data" not in str(e):
            raise
        th = None
    if th is None or th.empty:  # a fund without published holdings, or not a fund at all: ask what it is
        if tk.info.get("quoteType") in ("ETF", "MUTUALFUND"):
            return []
        raise LookupError(f"{ticker}: not a fund")
    return [{"symbol": str(sym), "name": str(r.get("Name") or sym), "weight": float(r["Holding Percent"])}
            for sym, r in th.iterrows()]


def fund_holdings(ticker: str, cache_dir: Path = CACHE, max_age_hours: float = 20,
                  fetch: Callable[[str], list[dict]] | None = None) -> dict | None:
    """None when the ticker is not a fund; otherwise its top holdings and the share of the fund they cover."""
    if ticker.startswith("^"):  # an index stands in for the fund: no holdings to read
        return {"ticker": ticker, "holdings": [], "covered": 0.0, "no_data": True}
    fetch = fetch or yf_top_holdings
    f = Path(cache_dir) / (ticker.replace("^", "_").replace("=", "_") + ".json")
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        if time.time() - d.get("fetched", 0) < max_age_hours * 3600:
            return d if d.get("fund", True) else None
    try:
        rows = fetch(ticker)
        d = None
    except LookupError:
        rows, d = None, {"ticker": ticker, "fund": False, "fetched": time.time()}
    if rows is not None:
        covered = sum(r["weight"] for r in rows)
        if covered > 1.0001:
            raise ValueError(f"{ticker}: fund weights add up to {covered:.2f}; expected fractions of the fund")
        d = {"ticker": ticker, "holdings": rows, "covered": covered, "fetched": time.time()}
        if not rows:  # a fund, but Yahoo lists none of its holdings
            d["no_data"] = True
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d), encoding="utf-8")
    return d if rows is not None else None


def look_through(values: dict[str, float], cash: float, funds: dict[str, dict | None]) -> dict:
    total = sum(values.values()) + cash
    comp: dict[str, dict] = {}
    rest, no_data = 0.0, []

    def add(key: str, name: str, eur: float, fund: str | None) -> None:
        c = comp.setdefault(key, {"name": name, "direct": 0.0, "via_funds": 0.0, "value": 0.0, "share": 0.0, "funds": {}})
        if c["name"] == key and name != key:  # a fund's list gives the company name a bare ticker lacks
            c["name"] = name
        if fund is None:
            c["direct"] += eur
        else:
            c["via_funds"] += eur
            c["funds"][fund] = c["funds"].get(fund, 0.0) + eur
        c["value"] += eur

    for t, v in values.items():
        f = funds.get(t)
        if f is None:
            add(company_key(t), t, v, None)
        elif f.get("no_data"):
            rest += v
            no_data.append(t)
        else:
            for h in f["holdings"]:
                add(company_key(h["symbol"]), h.get("name") or h["symbol"], v * h["weight"], t)
            rest += v * (1 - f["covered"])
    for c in comp.values():
        c["share"] = c["value"] / total if total else 0.0
    return {"total": total, "companies": comp, "not_broken_down": rest, "no_data": no_data}


def share_after(values: dict[str, float], cash: float, funds: dict[str, dict | None], ticker: str, amount: float,
                cand_fund: dict | None) -> dict:
    v = dict(values)
    v[ticker] = v.get(ticker, 0.0) + amount
    return look_through(v, cash, {**funds, ticker: cand_fund if cand_fund is not None else funds.get(ticker)})


def resolve_funds(tickers: list[str], get_fund: Callable[[str], dict | None], stand_in: dict[str, str]) -> dict[str, dict | None]:
    """Fund holdings per held ticker (a stand-in ticker where configured); a failed fetch counts as no data for this run."""
    out: dict[str, dict | None] = {}
    for t in dict.fromkeys(tickers):
        try:
            out[t] = get_fund(stand_in.get(t, t))
        except Exception:
            out[t] = {"ticker": t, "holdings": [], "covered": 0.0, "no_data": True}
    return out


def top_companies(lt: dict, n: int = 5) -> dict:
    """The n largest companies as portfolio shares (no euro amounts), plus what is not broken down."""
    tot = lt["total"] or 1.0
    rows = sorted(lt["companies"].items(), key=lambda kv: -kv[1]["value"])[:n]
    return {"top": [{"key": k, "name": c["name"], "share": round(c["value"] / tot, 4), "direct": round(c["direct"] / tot, 4),
                     "via_funds": round(c["via_funds"] / tot, 4)} for k, c in rows],
            "not_broken_down": round(lt["not_broken_down"] / tot, 4), "no_data": lt["no_data"],
            "source": "Yahoo Finance fund top holdings"}


def portfolio_lookthrough(holdings_path, instruments_path, get_fund: Callable[[str], dict | None], n: int = 5) -> dict:
    from .config import load_holdings, load_instruments

    h = load_holdings(holdings_path)
    values: dict[str, float] = {}
    for p in h.positions:
        if p.ticker:
            values[p.ticker] = values.get(p.ticker, 0.0) + p.value_eur
    cash = h.cash_eur + sum(p.value_eur for p in h.positions if not p.ticker)  # as the risk numbers count them
    stand_in = {i.ticker: i.holdings_from for i in load_instruments(instruments_path).values() if i.holdings_from}
    lt = look_through(values, cash, resolve_funds(list(values), get_fund, stand_in))
    for p in h.positions:  # a direct holding no fund names: use the report's name rather than the bare ticker
        c = lt["companies"].get(company_key(p.ticker)) if p.ticker else None
        if c and c["name"] == p.ticker:
            c["name"] = p.name
    return top_companies(lt, n)


def format_top(block: dict) -> str:
    lines = ["Largest companies, including funds"]
    for r in block["top"]:
        via = f", {r['via_funds']:.1%} through funds" if r["via_funds"] >= 0.0005 else ""
        lines.append(f"  {r['name'][:32]:32} {r['share']:6.1%}{via}")
    lines.append(f"{block['not_broken_down']:.0%} not broken down (fund money outside the published top holdings).")
    if block["no_data"]:
        lines.append("No holdings data: " + ", ".join(block["no_data"]))
    lines.append("Source: " + block["source"] + ".")
    return "\n".join(lines)
