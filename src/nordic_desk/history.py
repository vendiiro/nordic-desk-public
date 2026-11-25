"""Analyst history: a dated snapshot per ticker on each card run, the change since the previous one,
and alerts when a stock crosses its buy or sell threshold.

Stored in data/analysts_history.csv (git-ignored). One row per ticker and day; a rerun the same day replaces it.
"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

PATH = Path("data/analysts_history.csv")
FIELDS = ["date", "ticker", "price", "target_mean", "target_low", "target_high", "n_analysts", "rating_share", "status"]
CROSSINGS = ("below buy threshold", "above sell threshold")


def _read(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v):
    if v in (None, ""):
        return None
    x = float(v)
    return x if math.isfinite(x) else None


def append_snapshot(card: dict, date: str, path: Path = PATH) -> None:
    a = card.get("analysts") or {}
    price = (card.get("price") or {}).get("close") or [None]
    row = {"date": date, "ticker": card["ticker"], "price": price[-1], "target_mean": a.get("target_mean"),
           "target_low": a.get("target_low"), "target_high": a.get("target_high"), "n_analysts": a.get("count"),
           "rating_share": a.get("rating_share"), "status": a.get("status")}
    rows = [r for r in _read(path) if not (r["date"] == date and r["ticker"] == card["ticker"])] + [
        {k: ("" if v is None else v) for k, v in row.items()}]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")  # write aside, then swap in: a crash never leaves half a history
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["ticker"], r["date"])))
    os.replace(tmp, path)


def previous(ticker: str, before: str, path: Path = PATH) -> dict | None:
    rows = [r for r in _read(path) if r["ticker"] == ticker and r["date"] < before]
    if not rows:
        return None
    r = max(rows, key=lambda r: r["date"])
    return {"date": r["date"], "target_mean": _num(r["target_mean"]), "rating_share": _num(r["rating_share"]),
            "status": r["status"] or None}


def change_since(card: dict, prev: dict | None) -> dict | None:
    if not prev:
        return None
    a = card.get("analysts") or {}
    tm, pm = a.get("target_mean"), prev.get("target_mean")
    rs, ps = a.get("rating_share"), prev.get("rating_share")
    return {"since": prev["date"], "target": (tm / pm - 1) if tm and pm else None,
            "rating_points": (rs - ps) * 100 if rs is not None and ps is not None else None,
            "status_before": prev.get("status")}


def alerts(cards: dict) -> list[dict]:
    """Cards whose status moved below the buy threshold or above the sell threshold since the previous snapshot."""
    out = []
    for t, c in cards.items():
        h, now = c.get("history"), (c.get("analysts") or {}).get("status")
        if h and now in CROSSINGS and h.get("status_before") != now:
            out.append({"ticker": t, "name": c.get("name") or t, "now": now, "before": h.get("status_before")})
    return out
