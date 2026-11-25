"""Analyst targets against what happened: the study's base rates until the desk has its own record."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import numpy as np
import pandas as pd

from .history import _num

STUDY = {"overshoot": 0.15, "met_12m": 0.38, "met_any": 0.64, "source": "Bradshaw, Brown & Huang (2013)"}
MIN_OWN = 30
HORIZON = 252
SPLIT_JUMP = 0.4  # |log return| in one day; a 2:1 split is 0.69, real one-day moves this large are rare


def monthly_snapshots(rows: list[dict]) -> list[dict]:
    """First snapshot per ticker per month: daily rows are near-copies, not new evidence."""
    first: dict[tuple[str, str], dict] = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        first.setdefault((r["ticker"], r["date"][:7]), r)
    return sorted(first.values(), key=lambda r: (r["date"], r["ticker"]))


def check(rows: list[dict], load_close: Callable[[str], pd.Series]) -> list[dict]:
    """Snapshots with 252 later trading days, judged on split-only closes (targets are price targets)."""
    out = []
    for r in rows:
        price, target = _num(r.get("price")), _num(r.get("target_mean"))
        c = load_close(r["ticker"]).dropna()
        if not price or not target or c.empty:
            continue
        j = c.index.searchsorted(pd.Timestamp(r["date"]))
        if j + HORIZON >= len(c):
            continue
        win = c.iloc[j:j + HORIZON + 1].to_numpy()
        if (np.abs(np.diff(np.log(win))) > SPLIT_JUMP).any():
            continue  # a split-sized one-day jump: the stored series isn't consistent across this window
        rel = win[1:] / win[0]  # ratios, so a later rescaling of the whole history doesn't matter
        need = target / price
        out.append({"ticker": r["ticker"], "date": r["date"], "implied": need - 1, "actual": float(rel[-1] - 1),
                    "met_12m": bool(rel[-1] >= need), "met_any": bool((rel >= need).any())})
    return out


def rates(checked: list[dict], first_date: str | None) -> dict:
    first = (date.fromisoformat(first_date) + timedelta(days=365)).isoformat() if first_date else None
    n = len(checked)
    if n < MIN_OWN:
        return {**STUDY, "n_checked": n, "first_check": first}
    return {"overshoot": float(np.mean([c["implied"] - c["actual"] for c in checked])),
            "met_12m": float(np.mean([c["met_12m"] for c in checked])), "met_any": float(np.mean([c["met_any"] for c in checked])),
            "source": f"own record ({n})", "n_checked": n, "first_check": first}


def realistic(upside: float | None, overshoot: float) -> float | None:
    return None if upside is None else upside - overshoot


def per_ticker(checked: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in checked:
        out[c["ticker"]] = out.get(c["ticker"], 0) + 1
    return out
