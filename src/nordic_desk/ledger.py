"""Forecast ledger: every range the desk shows is written down and later scored against what happened,
so the desk builds its own record (spec 2026-11-25-goal-range-design, idea G).

Rows live in data/ledger/forecasts.jsonl (git-ignored). Quantiles are returns, not euros. One row per kind per ISO week.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd

PATH = Path("data/ledger/forecasts.jsonl")
SHOW_FROM = 5  # matured rows before the page shows an own record


def make_row(made: str, kind: str, days: int, q: dict[str, float], drift: float | None, weights: dict[str, float]) -> dict:
    y, w, _ = date.fromisoformat(made).isocalendar()
    h = hashlib.sha256(json.dumps({t: round(x, 4) for t, x in sorted(weights.items())}).encode()).hexdigest()[:12]
    return {"made": made, "week": f"{y}-W{w:02d}", "kind": kind, "days": int(days), "q": q, "drift": drift,
            "weights": weights, "hash": h, "scored": None}


def read(path=PATH) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(path, rows: list[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in rows), encoding="utf-8")


def record(path, rows: list[dict]) -> int:
    """Append rows whose kind has no row yet in their week; returns how many were added."""
    old = read(path)
    seen = {(r["kind"], r["week"]) for r in old}
    new = []
    for r in rows:
        if (r["kind"], r["week"]) not in seen:
            seen.add((r["kind"], r["week"]))
            new.append(r)
    if new:
        _write(path, old + new)
    return len(new)


def pinball(q: dict[str, float], y: float) -> float:
    """Mean quantile (pinball) loss of the stored quantiles for the realised return y."""
    loss = [max(float(t) * (y - x), (float(t) - 1) * (y - x)) for t, x in q.items()]
    return sum(loss) / len(loss)


def score(path, panel: pd.DataFrame) -> int:
    """Score every unscored row whose horizon has passed in the panel; returns how many were scored."""
    rows, done = read(path), 0
    for r in rows:
        if r["scored"] is not None:
            continue
        made = pd.Timestamp(r["made"])
        after = panel.index[panel.index > made]
        before = panel.index[panel.index <= made]
        if len(after) < r["days"] or not len(before) or any(t not in panel for t in r["weights"]):
            continue
        start, end = before[-1], after[r["days"] - 1]
        real = sum(w * (panel.at[end, t] / panel.at[start, t] - 1) for t, w in r["weights"].items())
        lo, hi = min(r["q"].values()), max(r["q"].values())
        r["scored"] = {"end": end.strftime("%Y-%m-%d"), "realised": float(real), "inside": bool(lo <= real <= hi),
                       "pinball": pinball(r["q"], float(real))}
        done += 1
    if done:
        _write(path, rows)
    return done


def summary(rows: list[dict]) -> dict:
    """How many matured ranges held their outer band, overall and per kind."""
    m = [r for r in rows if r.get("scored")]
    by: dict[str, dict] = {}
    for r in m:
        k = by.setdefault(r["kind"], {"matured": 0, "held": 0})
        k["matured"] += 1
        k["held"] += r["scored"]["inside"]
    return {"matured": len(m), "held": sum(r["scored"]["inside"] for r in m), "pending": len(rows) - len(m),
            "show": len(m) >= SHOW_FROM, "by_kind": by, "first": min((r["made"] for r in rows), default=None)}
