"""Per-stock returns and risk over the last year of daily closes (in the stock's own currency).

Formulas follow docs/mockups/src/gen.py: log returns for volatility and beta, closes for the rest.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

WINDOW = 252  # daily returns in one year
OFFSETS = {"d1": 1, "w1": 5, "m1": 21, "m3": 63, "m6": 126, "y1": WINDOW}


def stock_stats(close: pd.Series, spy: pd.Series) -> dict:
    close = close.dropna().sort_index()
    c = close.to_numpy(dtype=float)
    win = c[-(WINDOW + 1):]
    out = {"last": c[-1], "prev": c[-2]}
    for key, n in OFFSETS.items():
        out[key] = c[-1] / c[-1 - n] - 1
    year_start = close[close.index < pd.Timestamp(year=close.index[-1].year, month=1, day=1)]
    out["ytd"] = c[-1] / year_start.iloc[-1] - 1 if len(year_start) else float("nan")
    hi, lo = float(win.max()), float(win.min())
    out.update(hi=hi, lo=lo, pos=(c[-1] - lo) / (hi - lo) if hi > lo else 1.0)
    r = np.diff(np.log(win))
    out["vol"] = float(np.std(r[-21:], ddof=1) * math.sqrt(WINDOW))
    peak = np.maximum.accumulate(win)
    out["mdd"] = float(min(0.0, (win / peak - 1).min()))
    s = spy.reindex(close.index).ffill().to_numpy(dtype=float)[-(WINDOW + 1):]
    rs = np.diff(np.log(s))
    out["beta"] = float(np.cov(r, rs, ddof=1)[0, 1] / np.var(rs, ddof=1))
    return {k: float(v) for k, v in out.items()}


def rebased(close: pd.Series, n: int = WINDOW) -> list[float]:
    c = close.dropna().sort_index().to_numpy(dtype=float)[-(n + 1):]
    return [float(v / c[0] * 100) for v in c]
