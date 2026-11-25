"""Which tickers get an analysis page, and the data each page embeds. All numbers are computed here, none in the browser."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .analysis_config import AnalysisConfig
from .config import load_holdings, load_instruments
from .explain import EXPLAIN
from .forecast import EXCLUDE
from .fundamentals import QUALITY_KEYS, eps_available, pe_reason
from .indicators import compute, pe_frame
from .quality import quality_detail
from .verdict import VERDICT_TABLE, entry_verdict, long_verdict
from .views.core import pct

GROUPS = ("held", "watch", "idea")
WINDOW = 1260  # trading days shown (5 years); indicators use the full history first
ARRAYS = {"c": "close", "o": "open", "h": "high", "l": "low", **{k: k for k in (
    "sma50", "sma200", "dist200", "bb_up", "bb_mid", "bb_lo", "pct_b", "rsi", "macd", "macd_signal", "macd_hist",
    "drawdown", "high52", "dist52", "vol", "mom", "ret3y", "chg_1w", "chg_1m", "chg_1y", "pe", "pe_pct", "pe_median")}}


@dataclass(frozen=True)
class Subject:
    ticker: str
    name: str
    groups: tuple[str, ...]
    note: str


def slug(ticker: str) -> str:
    return ticker.replace("^", "_").replace("=", "_")  # same as prices._file


def analysis_href(ticker: str) -> str | None:
    return None if ticker in EXCLUDE else f"analysis/{slug(ticker)}.html"


def subjects(holdings_path, instruments_path, watchlist: list[str], cards_doc: dict | None) -> list[Subject]:
    found: dict[str, dict] = {}

    def add(t: str, name: str, group: str, note: str = ""):
        if t in EXCLUDE:  # crypto test positions; other crypto is dropped by quote type in write_analysis
            return
        s = found.setdefault(t, {"name": name, "groups": set(), "note": note})
        s["groups"].add(group)

    notes = {i.name: i.note for i in load_instruments(instruments_path).values()} if Path(instruments_path).exists() else {}
    if Path(holdings_path).exists():
        for p in load_holdings(holdings_path).positions:
            if p.ticker:
                add(p.ticker, p.name, "held", notes.get(p.name, ""))
    for t in watchlist:
        add(t, t, "watch")
    cards = (cards_doc or {}).get("cards") or []
    for c in (cards.values() if isinstance(cards, dict) else cards):
        add(c["ticker"], c.get("name") or c["ticker"], "idea")
    return [Subject(t, v["name"], tuple(g for g in GROUPS if g in v["groups"]), v["note"]) for t, v in found.items()]


def kind_of(f: dict | None) -> str:
    qt = (f or {}).get("quote_type")
    if qt is None:
        return "unknown"  # company data not fetched yet: never call it a fund
    return "stock" if qt == "EQUITY" else "crypto" if qt == "CRYPTOCURRENCY" else "fund"


def _clean(x):
    if x is None:
        return None
    if isinstance(x, str):
        return x
    x = float(x)
    return round(x, 4) if math.isfinite(x) else None


def _f(x, fmt) -> str:
    return "–" if _clean(x) is None else fmt(x)


def _or(x, d):
    return d if x is None else x  # 0.0 is a real reading, not missing


def _verdict(v) -> dict | None:
    return None if v is None else {"v": v.v, "cls": v.cls, "line": v.line, "why": [list(w) for w in v.why]}


def payload(s: Subject, ohlc: pd.DataFrame, close_fallback: pd.Series, f: dict | None, cfg: AnalysisConfig,
            fx_to_usd: dict[str, float], built: str) -> dict:
    has_ohlc = not ohlc.empty
    df = ohlc if has_ohlc else pd.DataFrame({"open": np.nan, "high": np.nan, "low": np.nan, "close": close_fallback.astype(float)})
    ind = compute(df, cfg.entry.trend_lookback)
    kind = kind_of(f)
    reason = pe_reason(f) or (None if has_ohlc else "no split-only price history")
    if reason is None:
        ind = ind.join(pe_frame(ind["close"], eps_available(f["eps"], cfg.long.eps_lag_days), cfg.long))
    else:
        ind[["pe", "pe_pct", "pe_median", "pe_n"]] = np.nan
    tail = ind.iloc[-WINDOW:]
    worst = float(tail["drawdown"].min())
    q = (quality_detail({k: f.get(k) for k in QUALITY_KEYS} | {"currency": f.get("currency")}, cfg.quality, fx_to_usd,
                        sector=f.get("sector"), must_pass=cfg.quality.must_pass, distorted_roe_above=cfg.quality.distorted_roe_above)
         if kind == "stock" and f else None)
    index = {row: i for i, row in enumerate(VERDICT_TABLE)}
    rows = [dict(r, worst_dd=worst, pe_reason=reason) for r in tail.replace({np.nan: None}).to_dict("records")]
    entry_day = [index[(v.v, v.cls, v.line)] for v in (entry_verdict(r, cfg.entry) for r in rows)]
    long_day = [None if v is None else index[(v.v, v.cls, v.line)]
                for v in (long_verdict(r, kind, None, cfg.quality, cfg.long, today=False) for r in rows)]
    last = rows[-1]
    today_entry = entry_verdict(last, cfg.entry)
    today_long = long_verdict(last, kind, q, cfg.quality, cfg.long, today=True)
    trend = last["trend"]
    entry_boxes = [
        {"key": "sma200", "label": "Trend", "value": _f(last["dist200"], lambda x: pct(x) + " vs 200-day"),
         "text": {"up": "Long-term uptrend: the 200-day line is rising and the price is above it.",
                  "down": "Downtrend: the price is below a falling 200-day line."}.get(trend, "No clean trend right now.")},
        {"key": "bb", "label": "Stretch", "value": f"RSI {_f(last['rsi'], lambda x: f'{x:.0f}')} · %B {_f(last['pct_b'], lambda x: f'{x * 100:.0f}')}",
         "text": "Overbought: RSI above " + f"{cfg.entry.stretched_rsi:.0f}; evidence that a dip follows is weak." if _or(last["rsi"], 50) > cfg.entry.stretched_rsi
         else "Pulled back to the bottom of its normal range." if _or(last["pct_b"], 0.5) < cfg.entry.pullback_pct_b
         else "Pushed to the top of its normal range." if _or(last["pct_b"], 0.5) > 0.9
         else "Oversold or cooling off: RSI is low." if _or(last["rsi"], 50) < cfg.entry.pullback_rsi else "Inside its normal range."},
        {"key": "mom", "label": "Momentum", "value": _f(last["mom"], pct),
         "text": "Less than a year of prices." if last["mom"] is None else "A 12-month winner; that tends to continue for months."
         if last["mom"] > 0 else "A 12-month loser; momentum works against you."},
        {"key": "dd", "label": "Risk", "value": f"{_f(last['drawdown'], lambda x: pct(x, 0))} · vol {_f(last['vol'], lambda x: pct(x, 0, sign=False))}",
         "text": f"Below its peak by {_f(last['drawdown'], lambda x: pct(-x, 0, sign=False))}; expect swings of about "
                 f"{_f(last['vol'], lambda x: pct(x, 0, sign=False))} a year."}]
    if kind == "stock":
        long_boxes = [
            {"key": "pe", "label": "Valuation", "value": _f(last["pe"], lambda x: f"P/E {x:.1f}"),
             "text": reason or ("Not enough P/E history yet." if last["pe_pct"] is None
                                else f"Cheaper than {round((1 - last['pe_pct']) * 100)}% of days in the last 5 years.")},
            {"key": "quality", "label": "Quality", "value": "not available" if not q or q.score is None else f"score {q.score}",
             "text": "No company data." if not q else f"ROE {_f(f.get('returnOnEquity'), lambda x: pct(x, 0, sign=False))}, "
                     f"net margin {_f(f.get('profitMargins'), lambda x: pct(x, 0, sign=False))}, status {q.status}."}]
    elif kind == "unknown":
        na = {"value": "not available", "text": "Company data not fetched yet; run nordic-desk update."}
        long_boxes = [{"key": "pe", "label": "Valuation", **na}, {"key": "quality", "label": "Quality", **na}]
    else:
        na = {"value": "not available for funds", "text": "See the fund look-through on the Desk view."}
        long_boxes = [{"key": "pe", "label": "Valuation", **na}, {"key": "quality", "label": "Quality", **na}]
    long_boxes += [
        {"key": "ltrev", "label": "Long-term", "value": _f(last["ret3y"], lambda x: pct(x, 0) + " in 3 years"),
         "text": "Huge 3-year run: long-run winners tend to cool." if _or(last["ret3y"], 0) > cfg.long.big_3y else "No extreme 3-year run."},
        {"key": "dd", "label": "Risk", "value": "worst " + pct(worst, 0),
         "text": "A fall this deep happened in the last 5 years; size your lump for it."}]
    fcf = f.get("freeCashflow") if f else None
    mcap = f.get("marketCap") if f else None
    out = {"ticker": s.ticker, "name": s.name, "note": s.note, "groups": list(s.groups), "kind": kind,
           "currency": (f or {}).get("currency"), "built": built, "has_ohlc": has_ohlc,
           "dates": [d.strftime("%Y-%m-%d") for d in tail.index],
           **{k: [_clean(v) for v in tail[col]] for k, col in ARRAYS.items()},
           "trend": [t if isinstance(t, str) else None for t in tail["trend"]], "pe_reason": reason,
           "verdicts": [{"v": v, "cls": c, "line": l} for v, c, l in VERDICT_TABLE],
           "entry_day": entry_day, "long_day": long_day,
           "today": {"entry": _verdict(today_entry), "long": _verdict(today_long)},
           "quality": None if q is None else {"score": q.score, "status": q.status, "checks": q.checks,
                                              "fcf_yield": _clean(fcf / mcap) if fcf and mcap else None},
           "boxes": {"entry": entry_boxes, "long": long_boxes}, "explain": EXPLAIN,
           "defaults": {"entry": {"range": 252, "style": "candle" if has_ohlc else "line", "on": ["sma200", "bb", "h52", "rsi"]},
                        "long": {"range": WINDOW, "style": "line", "on": ["sma200", "dd"] + (["pe"] if kind == "stock" else [])}}}
    if out["quality"]:
        out["quality"]["checks"] = [{k: _clean(v) if k == "value" else v for k, v in c.items()} for c in q.checks]
    return out


def index_row(p: dict) -> dict:
    """One screener row for the Analysis front page, read off a stock's page payload (no new maths)."""
    c = [x for x in p["c"] if x is not None]
    last = lambda k: p[k][-1] if p.get(k) else None
    lo, hi = min(c[-252:]), max(c[-252:] + [last("high52") or c[-1]])
    v = p["today"]["entry"]
    return {"ticker": p["ticker"], "name": p["name"], "group": (p.get("groups") or ["watch"])[0], "kind": p["kind"],
            "price": c[-1], "d1": c[-1] / c[-2] - 1 if len(c) > 1 else None, "currency": p.get("currency"),
            "verdict": v["v"], "cls": v["cls"], "line": v["line"],
            "dist200": last("dist200"), "rsi": last("rsi"), "pct_b": last("pct_b"), "mom": last("mom"),
            "drawdown": last("drawdown"), "vol": last("vol"), "pe_pct": last("pe_pct"),
            "spark": [round(x, 4) for x in c[-63:]], "pos52": (c[-1] - lo) / (hi - lo) if hi > lo else 0.5,
            "expected": None, "upside": None, "changed": False}


def track_for(line: str, per_stock: dict | None) -> dict | None:
    """Today's verdict group with this stock's own past record in it, for the line under the verdict."""
    from .scorecard import GROUPS, LABELS
    g = GROUPS.get(line)
    if g is None or per_stock is None:
        return None
    return {"group": g, "label": LABELS[g], "stats": per_stock.get(g)}


def remember(prev: dict, rows: list[dict], close: str | None) -> dict:
    """Mark rows whose verdict differs from the last verdicts of an earlier close; rebuilding on the same close keeps that base."""
    if prev.get("close") is not None and prev.get("close") == close:
        base = prev.get("base") or {}
    else:
        old = prev["rows"] if "rows" in prev else prev  # older files: ticker -> word or row
        base = {t: v.get("verdict") if isinstance(v, dict) else v for t, v in old.items()}
    for r in rows:
        r["changed"] = base.get(r["ticker"]) not in (None, r["verdict"])
    return {"close": close, "base": base,
            "rows": {r["ticker"]: {k: r[k] for k in ("verdict", "cls", "line", "expected", "name", "group", "changed")} for r in rows}}


def write_analysis(out_dir: Path, watchlist: list[str], holdings_path: str = "config/holdings.local.toml",
                   instruments_path: str = "config/instruments.toml", price_root: Path | None = None,
                   ohlc_root: Path | None = None, fund_root: Path | None = None, forecasts: dict | None = None,
                   close: str | None = None) -> list[Path]:
    """One page per subject from the local caches (no network), plus an index. Subjects without any prices are skipped."""
    import json
    from datetime import date

    from . import fundamentals, ohlc, prices
    from .analysis_config import load
    from .views.analysis import analysis_index, analysis_page

    price_root, ohlc_root, fund_root = price_root or prices.ROOT, ohlc_root or ohlc.ROOT, fund_root or fundamentals.ROOT
    cards = Path(out_dir) / "cards.json"
    subs = subjects(holdings_path, instruments_path, watchlist, json.loads(cards.read_text(encoding="utf-8")) if cards.exists() else None)
    eurusd = prices.load("EURUSD=X", price_root)
    fx = {"USD": 1.0, **({"EUR": float(eurusd.iloc[-1])} if not eurusd.empty else {})}
    cfg, built = load(), date.today().isoformat()
    ready = []
    for s in subs:
        f = fundamentals.load_fundamentals(s.ticker, fund_root)
        o, c = ohlc.load_ohlc(s.ticker, ohlc_root), prices.load(s.ticker, price_root)
        if kind_of(f) != "crypto" and not (o.empty and c.empty):
            ready.append((s, f, o, c))
    site = Path(out_dir) / "site" / "analysis"
    site.mkdir(parents=True, exist_ok=True)
    picker, written, rows = [s for s, *_ in ready], [], []
    prev_file = Path(out_dir) / "analysis_index.json"
    prev = json.loads(prev_file.read_text(encoding="utf-8")) if prev_file.exists() else {}
    fc = forecasts or {}
    upside = {x["ticker"]: x["upside"] for x in (fc.get("targets") or {}).get("rows", [])}
    for s, f, o, c in ready:
        p = site / f"{slug(s.ticker)}.html"
        pl = payload(s, o, c, f, cfg, fx, built)
        per = ((forecasts or {}).get("scorecard") or {}).get("126", {}).get("per_stock", {})
        pl["track"] = track_for(pl["today"]["entry"]["line"], per.get(s.ticker)) if forecasts else None
        pl["expected"] = (fc.get("expected") or {}).get(s.ticker)
        p.write_text(analysis_page(pl, picker), encoding="utf-8")
        row = index_row(pl)
        row["expected"] = pl["expected"]["combined"] if pl["expected"] and pl["expected"]["pieces"] else None  # anchor alone is not a stock view
        row["upside"] = upside.get(s.ticker)
        rows.append(row)
        written.append(p)
    doc = remember(prev, rows, close)
    (site / "index.html").write_text(analysis_index(picker, rows), encoding="utf-8")
    prev_file.write_text(json.dumps(doc, allow_nan=False), encoding="utf-8")
    return written + [site / "index.html"]
