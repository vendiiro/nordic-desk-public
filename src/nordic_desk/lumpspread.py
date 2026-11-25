"""Lump sum now versus equal monthly parts, over every past monthly start date. Values are per 1 EUR invested."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .scorecard import month_starts


def outcomes(close_eur: pd.Series, k: int, horizon: int = 252) -> pd.DataFrame:
    """Per start s: L = lump value and S = spread value, both at index(s) + horizon. Idle cash earns 0%."""
    c = close_eur.dropna()
    pos = {d: i for i, d in enumerate(c.index)}
    starts = [pos[d] for d in month_starts(c.index)]
    v = c.to_numpy()
    rows = []
    for n, i in enumerate(starts):
        end = i + horizon
        buys = starts[n:n + k]
        if end >= len(c) or len(buys) < k or buys[-1] > end:
            continue
        p_end = v[end]
        rows.append({"start": c.index[i], "L": p_end / v[i], "S": float(np.mean(p_end / v[buys]))})
    return pd.DataFrame(rows, columns=["start", "L", "S"])


def lump_vs_spread(close_eur: pd.Series, k: int, horizon: int = 252, bins: int = 20) -> dict | None:
    o = outcomes(close_eur, k, horizon)
    if o.empty:
        return None
    diff = (o["L"] - o["S"]).to_numpy()
    lo, hi = float(diff.min()), float(diff.max())
    if hi - lo < 1e-12:
        lo, hi = lo - 0.01, hi + 0.01  # all equal: one visible bin around the value
    counts, edges = np.histogram(diff, bins=bins, range=(lo, hi))
    return {"starts": int(len(o)), "lump_ahead": float((diff > 1e-12).mean()), "median_diff": float(np.median(diff)),
            "lump_median": float(o["L"].median()), "spread_median": float(o["S"].median()),
            "lump_p5": float(o["L"].quantile(0.05)), "spread_p5": float(o["S"].quantile(0.05)),
            "worst_lump_regret": float(diff.min()), "worst_spread_regret": float((-diff).min()),
            "hist": {"edges": [float(e) for e in edges], "counts": [int(x) for x in counts]}}


def vs_value(p: np.ndarray, i: int, later: list[int], end: int, f: float) -> float:
    """Vol-sized value per 1 EUR: f bought at i, the rest in equal parts at the later month starts, all valued at end."""
    return float(f * p[end] / p[i] + (1 - f) / len(later) * np.sum(p[end] / p[later]))


def vs_outcomes(close_eur: pd.Series, k: int, horizon: int = 252) -> pd.DataFrame:
    """Per start with a usual volatility on record: first part f (point in time), vol-sized V, lump L and spread S."""
    from .volsize import first_part, usual_series, vol63
    c = close_eur.dropna()
    v = c.to_numpy()
    vol = vol63(c).to_numpy()
    usual = usual_series(vol63(c)).to_numpy()
    pos = {d: i for i, d in enumerate(c.index)}
    starts = [pos[d] for d in month_starts(c.index)]
    rows = []
    for n, i in enumerate(starts):
        end = i + horizon
        later, spread = starts[n + 1:n + 1 + k], starts[n:n + k]
        if np.isnan(usual[i]) or end >= len(c) or len(later) < k or later[-1] > end:
            continue
        f = first_part(float(vol[i]), float(usual[i]))
        rows.append({"start": c.index[i], "f": f, "V": vs_value(v, i, later, end, f), "L": v[end] / v[i],
                     "S": float(np.mean(v[end] / v[spread]))})
    return pd.DataFrame(rows, columns=["start", "f", "V", "L", "S"])


def volsized(close_eur: pd.Series, k: int, horizon: int = 252) -> dict | None:
    """Vol-sized against lump and spread, judged only where it actually held back (f below 1)."""
    o = vs_outcomes(close_eur, k, horizon)
    if o.empty:
        return None
    held = o[o["f"] < 1.0]
    out = {"starts": int(len(o)), "held_back": int(len(held)), "beat_lump": None, "beat_spread": None, "median": None,
           "p5": None, "lump_median": None, "spread_median": None, "lump_p5": None, "spread_p5": None, "f_median": None}
    if held.empty:
        return out
    return out | {"beat_lump": float((held["V"] > held["L"]).mean()), "beat_spread": float((held["V"] > held["S"]).mean()),
                  "median": float(held["V"].median()), "p5": float(held["V"].quantile(0.05)),
                  "lump_median": float(held["L"].median()), "spread_median": float(held["S"].median()),
                  "lump_p5": float(held["L"].quantile(0.05)), "spread_p5": float(held["S"].quantile(0.05)),
                  "f_median": float(held["f"].median())}
