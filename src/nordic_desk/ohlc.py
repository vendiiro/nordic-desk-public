"""Daily open/high/low/close (split-adjusted, not dividend-adjusted) for candle charts and P/E history; same naming and update rules as prices.py."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from .prices import DEFAULT_START, _file

ROOT = Path("data/ohlc_split")  # split-adjusted only; dividend-adjusted closes would bias P/E history
COLS = ["open", "high", "low", "close"]


def load_ohlc(ticker: str, root: Path = ROOT) -> pd.DataFrame:
    f = _file(ticker, root)
    if not f.exists():
        return pd.DataFrame(columns=COLS, index=pd.DatetimeIndex([]), dtype=float)
    return pd.read_csv(f, index_col=0, parse_dates=True)[COLS].astype(float)


def yf_fetch_ohlc(ticker: str, start: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(ticker, start=start, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=COLS, dtype=float)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower() for c in df.columns]
    return df[COLS].dropna().astype(float)


def update_ohlc(tickers: list[str], start: str = DEFAULT_START, root: Path = ROOT,
                fetch: Callable[[str, str], pd.DataFrame] = yf_fetch_ohlc) -> dict[str, str]:
    Path(root).mkdir(parents=True, exist_ok=True)
    status: dict[str, str] = {}
    for t in tickers:
        old = load_ohlc(t, root)
        try:
            new = fetch(t, min(start, old.index[0].strftime("%Y-%m-%d")) if not old.empty else start)  # whole history each time, so splits re-adjust the past consistently
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
        out = new[COLS].sort_index()
        out = out[~out.index.duplicated(keep="last")]
        out.index.name = "date"
        out.to_csv(_file(t, root))
        status[t] = "ok"
    return status
