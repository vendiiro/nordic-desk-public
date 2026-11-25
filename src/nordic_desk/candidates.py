"""Yahoo search and per-ticker candidate data (company facts, analyst ratings and targets, annual results), cached.

Only listings on the exchanges in ALLOWED_EXCHANGES and of type stock or ETF are kept, so the cards never mix
thin or duplicate listings (spec: docs/superpowers/specs/2026-11-18-search-and-signals-design.md).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

ALLOWED_EXCHANGES = {"NYQ", "NMS", "NGM", "NCM", "ASE", "PCX", "BTS", "HEL", "GER"}
ALLOWED_TYPES = {"EQUITY", "ETF"}
CACHE = Path("data/candidates")


class CandidateError(RuntimeError):
    pass


def yf_search(text: str) -> list[dict]:
    import yfinance as yf

    return yf.Search(text, max_results=20).quotes or []


def search(text: str, fetch: Callable[[str], list[dict]] = yf_search) -> list[dict]:
    out = []
    for q in fetch(text):
        if q.get("exchange") in ALLOWED_EXCHANGES and q.get("quoteType") in ALLOWED_TYPES:
            out.append({"symbol": q["symbol"], "name": q.get("shortname") or q.get("longname") or q["symbol"],
                        "exchange": q["exchange"], "type": q["quoteType"]})
    return out


def yf_info(t: str) -> dict:
    import yfinance as yf

    return yf.Ticker(t).info or {}


def yf_recs(t: str) -> dict:
    import yfinance as yf

    r = yf.Ticker(t).recommendations
    if r is None or r.empty:
        return {}
    row = r.iloc[0]  # period "0m": the latest month
    return {k: int(row[k]) for k in ("strongBuy", "buy", "hold", "sell", "strongSell") if k in row}


def yf_fin(t: str) -> list[dict]:
    import yfinance as yf

    f = yf.Ticker(t).income_stmt
    if f is None or f.empty:
        return []
    out = []
    for col in list(f.columns)[:4]:
        rev = f.at["Total Revenue", col] if "Total Revenue" in f.index else None
        ni = f.at["Net Income", col] if "Net Income" in f.index else None
        ok = lambda v: None if v is None or v != v else float(v)
        out.append({"year": int(str(col)[:4]), "revenue": ok(rev), "net_income": ok(ni)})
    return out


def fetch_candidate(ticker: str, fetch_info=yf_info, fetch_recs=yf_recs, fetch_fin=yf_fin) -> dict:
    i = fetch_info(ticker)
    qtype = i.get("quoteType")
    return {
        "ticker": ticker, "name": i.get("longName") or i.get("shortName") or ticker, "sector": i.get("sector"),
        "industry": i.get("industry"), "currency": i.get("currency"), "quote_type": qtype, "market_cap": i.get("marketCap"),
        "target_mean": i.get("targetMeanPrice"), "target_low": i.get("targetLowPrice"), "target_high": i.get("targetHighPrice"),
        "n_analysts": i.get("numberOfAnalystOpinions") or 0,
        "rating_counts": fetch_recs(ticker) if qtype == "EQUITY" else {},
        "results": fetch_fin(ticker) if qtype == "EQUITY" else [],
        "fetched": time.time(),
    }


def load_or_fetch(ticker: str, cache_dir: Path = CACHE, max_age_hours: float = 20, **fetchers) -> dict:
    f = Path(cache_dir) / (ticker.replace("^", "_").replace("=", "_") + ".json")
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        if time.time() - d.get("fetched", 0) < max_age_hours * 3600:
            return d
    try:
        d = fetch_candidate(ticker, **fetchers)
    except Exception as e:
        raise CandidateError(f"{ticker}: {e}") from e
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(d), encoding="utf-8")
    return d
