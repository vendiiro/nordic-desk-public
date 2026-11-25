"""Company facts for the analysis page: quote type, quality fields and annual EPS history, cached as JSON per ticker."""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from .prices import _file

ROOT = Path("data/fundamentals")
QUALITY_KEYS = ("returnOnEquity", "profitMargins", "debtToEquity", "freeCashflow", "revenueGrowth", "marketCap")


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def yf_info(t: str) -> dict:
    import yfinance as yf

    return yf.Ticker(t).info or {}


def yf_eps(t: str) -> list[dict]:
    import yfinance as yf

    f = yf.Ticker(t).income_stmt
    if f is None or f.empty:
        return []
    row = next((r for r in ("Diluted EPS", "Basic EPS") if r in f.index), None)
    if row is None:
        return []
    return [{"year_end": str(col)[:10], "eps": v} for col in f.columns if (v := _num(f.at[row, col])) is not None]


def fetch_fundamentals(ticker: str, fetch_info: Callable[[str], dict] = yf_info,
                       fetch_eps: Callable[[str], list[dict]] = yf_eps) -> dict:
    i = fetch_info(ticker)
    qt = i.get("quoteType")
    return {"ticker": ticker, "name": i.get("shortName") or i.get("longName") or ticker, "quote_type": qt,
            "currency": i.get("currency"), "financial_currency": i.get("financialCurrency") or i.get("currency"),
            "sector": i.get("sector"), **{k: _num(i.get(k)) for k in QUALITY_KEYS},
            "eps": fetch_eps(ticker) if qt == "EQUITY" else [], "fetched": date.today().isoformat()}


def _path(ticker: str, root: Path) -> Path:
    return _file(ticker, root).with_suffix(".json")


def load_fundamentals(ticker: str, root: Path = ROOT) -> dict | None:
    p = _path(ticker, root)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def update_fundamentals(tickers: list[str], root: Path = ROOT,
                        fetch: Callable[[str], dict] = fetch_fundamentals) -> dict[str, str]:
    Path(root).mkdir(parents=True, exist_ok=True)
    status = {}
    for t in tickers:
        try:
            f = fetch(t)
        except Exception as e:  # keep the old file; one bad ticker never stops the others
            status[t] = f"error: {e}"
            continue
        if not f.get("quote_type"):  # empty answer from Yahoo: keep what we had
            status[t] = "error: no data from Yahoo"
            continue
        _path(t, root).write_text(json.dumps(f, indent=1, allow_nan=False), encoding="utf-8")
        status[t] = "ok"
    return status


def eps_available(eps: list[dict], lag_days: int) -> list[tuple[pd.Timestamp, float]]:
    """EPS by the day it became public: fiscal year-end + lag (report dates are not stored)."""
    return sorted((pd.Timestamp(r["year_end"]) + pd.Timedelta(days=lag_days), float(r["eps"])) for r in eps)


PE_REASONS = ("not a company (fund or index)", "no earnings history", "earnings reported in another currency",
              "no split-only price history")


def pe_reason(f: dict | None) -> str | None:
    """Why P/E can't be shown, or None when it can."""
    if f and f.get("quote_type") not in (None, "EQUITY"):
        return "not a company (fund or index)"
    if not f or not f.get("eps"):
        return "no earnings history"
    if f.get("financial_currency") != f.get("currency"):
        return "earnings reported in another currency"
    return None
