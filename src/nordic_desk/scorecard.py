"""Scorecard: rebuild past entry verdicts from prices (point in time) and score them against SPY afterwards."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .analysis_config import EntryTh
from .eur import asof
from .indicators import compute
from .verdict import DOWN, MIXED, PULLBACK, STEADY, STRETCHED, entry_verdict

GROUPS = {PULLBACK[2]: "pullback", STEADY[2]: "steady", STRETCHED[2]: "stretched", DOWN[2]: "wait_down", MIXED[2]: "wait_mixed"}
LABELS = {"pullback": "Good entry · pullback", "steady": "Good entry · steady", "stretched": "Stretched",
          "wait_down": "Wait · trend down", "wait_mixed": "Wait · no clear trend"}
GOOD = {"pullback", "steady"}
MIN_WINDOWS = 12


def verdict_series(ohlc: pd.DataFrame, th: EntryTh) -> pd.Series:
    ind = compute(ohlc, th.trend_lookback)  # every indicator looks only backwards, so each day's verdict is point in time
    rows = ind.replace({np.nan: None}).to_dict("records")
    return pd.Series([GROUPS.get(entry_verdict(r, th).line) for r in rows], index=ind.index, dtype=object)


def month_starts(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period("M")).first().values)


def samples(groups: pd.Series, stock_eur: pd.Series, spy_eur: pd.Series, H: int) -> pd.DataFrame:
    stock = stock_eur.dropna()
    spy_on = asof(spy_eur, stock.index).to_numpy()  # SPY as of each stock date, looked up once
    rows = []
    for d in month_starts(groups.index):
        g = groups.get(d)
        j = stock.index.searchsorted(d)
        if g is None or j + H >= len(stock) or stock.index[j].to_period("M") != d.to_period("M"):
            continue  # no price that month (series starts later or has a gap): never reuse another month's entry
        s0, s1 = spy_on[j], spy_on[j + H]
        if np.isnan(s0) or np.isnan(s1):
            continue
        ex = (stock.iloc[j + H] / stock.iloc[j] - 1) - (s1 / s0 - 1)
        rows.append({"date": d, "month": d.to_period("M"), "group": g, "excess": float(ex), "beat": bool(ex > 0)})
    return pd.DataFrame(rows, columns=["date", "month", "group", "excess", "beat"])


def nw_interval(x: np.ndarray, lag: int) -> tuple[float, float, float]:
    """Mean with a 95% interval from a Newey-West standard error (Bartlett weights)."""
    x = np.asarray(x, float)
    n = len(x)
    m = float(x.mean()) if n else math.nan
    if n < 2:
        return m, math.nan, math.nan
    d = x - m
    var = d @ d / n
    for l in range(1, min(lag, n - 1) + 1):
        var += 2 * (1 - l / (lag + 1)) * (d[l:] @ d[:-l]) / n
    se = math.sqrt(max(var, 0.0) / n)
    return m, m - 1.96 * se, m + 1.96 * se


def group_stats(s: pd.DataFrame, H: int, good: bool) -> dict:
    h = max(1, H // 21)
    monthly = s.groupby("month")["excess"].mean().sort_index()  # stocks in the same month move together
    mean, lo, hi = nw_interval(monthly.to_numpy(), h - 1)  # windows overlap by (h-1)/h
    eff = len(monthly) / h
    if eff < MIN_WINDOWS or math.isnan(lo):
        reading = "too few"
    elif (lo > 0) if good else (hi < 0):
        reading = "helps"
    elif (hi < 0) if good else (lo > 0):
        reading = "works against"
    else:
        reading = "no clear edge"
    return {"n_samples": int(len(s)), "n_months": int(len(monthly)), "eff_windows": round(eff, 1),
            "beat": float(s["beat"].mean()) if len(s) else None, "mean": mean, "lo": lo, "hi": hi, "reading": reading}


def stock_reading(st: dict, pooled_reading: str, good: bool) -> str:
    """Per-stock lines never claim an edge on their own: many stocks are tested at once."""
    lo, hi = st.get("lo"), st.get("hi")
    clear = lo is not None and hi is not None and not math.isnan(lo) and ((lo > 0) if good else (hi < 0))
    if st.get("eff_windows", 0) >= MIN_WINDOWS and clear and pooled_reading == "helps":
        return "consistent with the pooled reading"
    return "too noisy to trust alone"
