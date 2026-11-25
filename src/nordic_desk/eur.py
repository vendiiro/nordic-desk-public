"""Close series in euros, read on each stock's own calendar (other series looked up as of each date)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .fundamentals import load_fundamentals

QUOTE_OK = ("EQUITY", "ETF", "MUTUALFUND")  # INDEX has no dividends and can't be bought; crypto is out


def asof(s: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Last value of s on or before each date in index (NaN before s starts)."""
    s = s.dropna().sort_index()
    pos = s.index.searchsorted(index, side="right") - 1
    vals = np.where(pos >= 0, s.to_numpy()[np.clip(pos, 0, None)] if len(s) else np.nan, np.nan)
    return pd.Series(vals, index=index, dtype=float)


def eur_closes(close: pd.Series, currency: str | None, eurusd: pd.Series) -> pd.Series | None:
    if currency == "EUR":
        return close
    if currency == "USD":
        return close / asof(eurusd, close.index)  # EURUSD=X is USD per 1 EUR
    return None


def currency_of(ticker: str, fund_root: Path, instruments: dict) -> str | None:
    f = load_fundamentals(ticker, fund_root)
    if f and f.get("currency"):
        return f["currency"]
    return next((i.currency for i in instruments.values() if i.ticker == ticker), None)


def quote_ok(f: dict | None) -> bool:
    return bool(f) and f.get("quote_type") in QUOTE_OK
