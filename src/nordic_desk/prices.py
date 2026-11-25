"""Local price store: one CSV of daily closes per ticker, refetched in full from Yahoo on every update so splits and
dividends re-adjust the whole past consistently (adjusted closes = total return)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

ROOT = Path("data/prices")
DEFAULT_START = "2015-01-01"


def _file(ticker: str, root: Path) -> Path:
    return Path(root) / (ticker.replace("^", "_").replace("=", "_") + ".csv")


def load(ticker: str, root: Path = ROOT) -> pd.Series:
    f = _file(ticker, root)
    if not f.exists():
        return pd.Series(dtype=float, name=ticker, index=pd.DatetimeIndex([]))
    df = pd.read_csv(f, index_col=0, parse_dates=True)
    return df.iloc[:, 0].astype(float).rename(ticker)


def yf_fetch(ticker: str, start: str) -> pd.Series:
    import yfinance as yf

    df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna().astype(float)


def update(tickers: list[str], start: str = DEFAULT_START, root: Path = ROOT,
           fetch: Callable[[str, str], pd.Series] = yf_fetch) -> dict[str, str]:
    Path(root).mkdir(parents=True, exist_ok=True)
    status: dict[str, str] = {}
    for t in tickers:
        old = load(t, root)
        try:
            new = fetch(t, min(start, old.index[0].strftime("%Y-%m-%d")) if not old.empty else start)  # whole history each time: Yahoo re-adjusts the past after every split and dividend
        except Exception as e:  # one bad ticker never stops the others
            status[t] = f"error: {e}"
            continue
        if new.empty:
            status[t] = "empty" if old.empty else f"no new data (last {old.index[-1]:%Y-%m-%d})"
            continue
        if not old.empty and (new.index[0] > old.index[0] + pd.Timedelta(days=10) or new.index[-1] < old.index[-1] - pd.Timedelta(days=4)):
            status[t] = (f"kept stored history (last {old.index[-1]:%Y-%m-%d}): Yahoo returned only "
                         f"{new.index[0]:%Y-%m-%d} to {new.index[-1]:%Y-%m-%d}")  # never cut stored history at either end
            continue
        out = new.rename(t).sort_index()
        out = out[~out.index.duplicated(keep="last")]
        out.index.name = "date"
        out.to_frame(t).to_csv(_file(t, root))
        status[t] = "ok"
    return status


# ---- company facts (P/E, market cap, sector, earnings date), cached as JSON ----
INFO = Path("data/info.json")
_SUFFIXES = (" Corporation", ", Inc.", " Inc.", " Incorporated", " & Co.", " Platforms")


def _name(n: str | None) -> str | None:
    if not n:
        return None
    for cut in _SUFFIXES:
        n = n.replace(cut, "")
    n = n.strip().rstrip(",")
    return n.title() if n.isupper() else n


def yf_info(ticker: str) -> dict:
    import yfinance as yf

    return yf.Ticker(ticker).info or {}


def load_info(path: Path = INFO) -> dict:
    import json

    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def update_info(tickers: list[str], path: Path = INFO, fetch: Callable[[str], dict] = yf_info) -> dict[str, str]:
    import json
    from datetime import datetime, timezone

    info, status = load_info(path), {}
    for t in tickers:
        try:
            raw = fetch(t)
        except Exception as e:
            status[t] = f"error: {e}"
            continue
        if not raw:
            status[t] = "empty"
            continue
        ts = raw.get("earningsTimestamp")
        info[t] = {
            "name": _name(raw.get("shortName")), "sector": raw.get("sector"), "industry": raw.get("industry"),
            "market_cap": raw.get("marketCap"), "pe_trailing": raw.get("trailingPE"), "pe_forward": raw.get("forwardPE"),
            "dividend_yield": raw.get("dividendYield"),
            "earnings": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else None,
        }
        status[t] = "ok"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(info, indent=1), encoding="utf-8")
    return status
