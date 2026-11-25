"""Where the portfolio could be in 1-10 years: a block bootstrap of its own daily returns in euros, re-centred on a stated
yearly return, with a lump, monthly savings, a goal and a drawdown limit; plus a point-in-time back-test of the one-year range.

Spec: docs/superpowers/specs/2026-11-25-goal-range-design.md. Everything runs on local prices; nothing leaves the computer.
"""
from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .forecast import EXCLUDE, _kupiec

PATH = "config/goals.local.toml"
YEAR, MONTH, MAX_YEARS = 252, 21, 10
QS = (0.05, 0.25, 0.5, 0.75, 0.95)
SENSITIVITY = 0.02  # the goal chance is repeated with the drift this much lower and higher
CHUNK = 500  # paths simulated at a time, to keep memory small over ten years of days


@dataclass(frozen=True)
class Goals:
    target_eur: float | None = None
    target_year: int | None = None
    monthly_eur: float = 0.0
    lump_eur: float = 0.0
    max_drawdown: float | None = None
    years: int = 5
    from_file: bool = False


def load_goals(path=PATH) -> Goals:
    """Goals from config/goals.local.toml; without the file, the range alone with no new money."""
    p = Path(path)
    if not p.exists():
        return Goals()
    d = tomllib.loads(p.read_text(encoding="utf-8"))
    known = {"target_eur", "target_year", "monthly_eur", "lump_eur", "max_drawdown", "years"}
    if set(d) - known:
        raise ValueError(f"{p}: unknown keys {', '.join(sorted(set(d) - known))}")
    years = int(d.get("years", 5))
    if not 1 <= years <= MAX_YEARS:
        raise ValueError(f"{p}: years must be 1 to {MAX_YEARS}")
    for k in ("monthly_eur", "lump_eur"):
        if float(d.get(k, 0)) < 0:
            raise ValueError(f"{p}: {k} cannot be negative")
    if ("target_eur" in d) != ("target_year" in d):
        raise ValueError(f"{p}: target_eur and target_year go together")
    if "target_eur" in d and float(d["target_eur"]) <= 0:
        raise ValueError(f"{p}: target_eur must be positive")
    mdd = d.get("max_drawdown")
    if mdd is not None and not 0 < float(mdd) < 1:
        raise ValueError(f"{p}: max_drawdown is a fraction between 0 and 1, such as 0.3")
    return Goals(float(d["target_eur"]) if "target_eur" in d else None, int(d["target_year"]) if "target_year" in d else None,
                 float(d.get("monthly_eur", 0)), float(d.get("lump_eur", 0)), float(mdd) if mdd is not None else None, years, True)


def portfolio_returns(panel: pd.DataFrame, values: dict[str, float], cash: float):
    """Daily portfolio returns in euros with today's weights fixed; excluded positions and cash earn 0%.
    Returns (returns, weights of the modelled positions, total value, excluded tickers), or None when nothing is modelled."""
    excluded = [t for t in values if t in EXCLUDE]
    model = {t: v for t, v in values.items() if t not in EXCLUDE}
    if not model:
        return None
    total = float(sum(values.values()) + cash)
    w = {t: v / total for t, v in model.items()}
    rp = panel[list(model)].pct_change().iloc[1:].to_numpy() @ np.array(list(w.values()))
    return rp, w, total, excluded


def recentre(lr, drift: float) -> np.ndarray:
    """Daily log returns with their own mean replaced by the stated yearly return; spread, tails and clustering stay."""
    lr = np.asarray(lr, dtype=float)
    return lr - lr.mean() + math.log1p(drift) / YEAR


def _add_years(d: date, y: int) -> date:
    try:
        return d.replace(year=d.year + y)
    except ValueError:  # 29 February
        return d.replace(year=d.year + y, day=28)


def _paths(lr: np.ndarray, days: int, n: int, block: int, seed: int):
    """Log growth at each month step (n, days/21 + 1) and each path's largest fall of the growth index."""
    if len(lr) < block:
        raise ValueError("too few days for a block bootstrap")
    rng = np.random.default_rng(seed)
    k = -(-days // block)
    starts = rng.integers(0, len(lr) - block + 1, size=(n, k))
    months, mdd = [], []
    for a in range(0, n, CHUNK):
        daily = lr[starts[a:a + CHUNK, :, None] + np.arange(block)].reshape(len(starts[a:a + CHUNK]), -1)[:, :days]
        c = np.concatenate([np.zeros((len(daily), 1)), np.cumsum(daily, axis=1)], axis=1)
        months.append(c[:, ::MONTH])
        mdd.append(1 - np.exp((c - np.maximum.accumulate(c, axis=1)).min(axis=1)))
    return np.concatenate(months), np.concatenate(mdd)


def _value(cm: np.ndarray, j: int, v0: float, m: float) -> np.ndarray:
    """Value after j months: the start value grown, plus one saving at each month start before j, each grown from its day."""
    grow = np.exp(cm[:, j:j + 1] - cm[:, :j]).sum(axis=1) if j else 0.0
    return v0 * np.exp(cm[:, j]) + m * grow


def _needed(cm: np.ndarray, j: int, v0: float, target: float) -> np.ndarray:
    """Monthly saving that reaches the target exactly on each path (value is linear in the saving for a fixed path)."""
    grow = np.exp(cm[:, j:j + 1] - cm[:, :j]).sum(axis=1)
    return np.maximum(0.0, (target - v0 * np.exp(cm[:, j])) / grow)


def simulate(rp, value: float, goals: Goals, drift: float, n: int = 5000, block: int = MONTH, seed: int = 0,
             today: date | None = None, invested: float = 1.0) -> dict:
    """`drift` is the yearly return of the invested part; cash (1 - invested) earns 0%, so the paths centre on invested * drift."""
    today = today or date.today()
    lr = recentre(np.log1p(np.asarray(rp, dtype=float)), invested * drift)
    v0, m = value + goals.lump_eur, goals.monthly_eur
    horizon, goal_years, note = goals.years, None, None
    if goals.target_eur is not None:
        ahead = goals.target_year - today.year
        if ahead < 1:
            note = "The target year has to be next year or later."
        elif ahead > MAX_YEARS:
            note = f"The range reaches at most {MAX_YEARS} years; pick a target year within {MAX_YEARS} years."
        else:
            goal_years, horizon = ahead, max(horizon, ahead)
    cm, mdd = _paths(lr, horizon * YEAR, n, block, seed)
    years = []
    for y in range(1, horizon + 1):
        v = _value(cm, 12 * y, v0, m)
        years.append({"year": y, "date": _add_years(today, y).isoformat(),
                      **{f"p{round(q * 100)}": float(x) for q, x in zip(QS, np.quantile(v, QS))},
                      "growth": {str(q): float(x) for q, x in zip(QS, np.expm1(np.quantile(cm[:, 12 * y], QS)))}})
    goal = None
    if goals.target_eur is not None:
        goal = {"target": goals.target_eur, "year": goals.target_year, "years_ahead": goal_years, "note": note,
                "prob": None, "prob_low": None, "prob_high": None, "monthly_50": None, "monthly_75": None}
        if goal_years:
            j = 12 * goal_years
            shift = lambda d: cm + (math.log1p(invested * d) - math.log1p(invested * drift)) * np.arange(cm.shape[1]) / 12  # noqa: E731
            chance = lambda c: float(np.mean(_value(c, j, v0, m) >= goals.target_eur))  # noqa: E731
            need = _needed(cm, j, v0, goals.target_eur)
            goal |= {"prob": chance(cm), "prob_low": chance(shift(drift - SENSITIVITY)), "prob_high": chance(shift(drift + SENSITIVITY)),
                     "monthly_50": float(np.quantile(need, 0.5)), "monthly_75": float(np.quantile(need, 0.75))}
    return {"drift": drift, "invested": invested, "sensitivity": SENSITIVITY, "n_paths": n, "block": block, "horizon_years": horizon,
            "start_value": v0, "monthly": m, "lump": goals.lump_eur, "years": years, "goal": goal,
            "contributions": [v0 + m * 12 * y for y in range(1, horizon + 1)],
            "drawdown": {"limit": goals.max_drawdown,
                         "prob_exceed": float(np.mean(mdd > goals.max_drawdown)) if goals.max_drawdown else None,
                         "p50": float(np.quantile(mdd, 0.5)), "p95": float(np.quantile(mdd, 0.95))}}


def backtest_1y(rp, drift: float, warm: int = 3 * YEAR, step: int = MONTH, n: int = 2000, block: int = MONTH, seed: int = 0,
                invested: float = 1.0) -> dict | None:
    """At every month start from `warm` days in: the one-year range from earlier days only, against what followed."""
    lr = np.log1p(np.asarray(rp, dtype=float))
    if len(lr) < warm + YEAR:
        return None
    k = -(-YEAR // block)
    checks = []
    for t in range(warm, len(lr) - YEAR + 1, step):
        cs = np.concatenate([[0.0], np.cumsum(recentre(lr[:t], invested * drift))])
        sums = cs[block:] - cs[:-block]
        draws = sums[np.random.default_rng([seed, t]).integers(0, len(sums), size=(n, k))].sum(axis=1)
        q5, q25, q75, q95 = (float(x) for x in np.quantile(draws, (0.05, 0.25, 0.75, 0.95)))
        real = float(lr[t:t + YEAR].sum())
        checks.append({"day": t, "q": [q5, q25, q75, q95], "realised": real,
                       "in90": bool(q5 <= real <= q95), "in50": bool(q25 <= real <= q75)})
    n_c = len(checks)
    h90, h50 = sum(c["in90"] for c in checks), sum(c["in50"] for c in checks)
    return {"n": n_c, "inside_90": h90 / n_c, "inside_50": h50 / n_c, "p_90": _kupiec(n_c - h90, n_c, 0.10),
            "p_50": _kupiec(n_c - h50, n_c, 0.50), "n_independent": n_c // 12, "checks": checks}


def build_goal(panel: pd.DataFrame, values: dict[str, float], cash: float, close: str, goals: Goals, drift: float,
               n: int = 5000, block: int = MONTH, risk: dict | None = None, ledger_path=None, anchor: dict | None = None,
               score_panel=None, record: bool = True) -> dict:
    """Everything the Goal page shows: the range, the goal box, the back-test and the ledger record (written as a side effect)."""
    from . import ledger

    pr = portfolio_returns(panel, values, cash)
    if pr is None:
        return {"available": False, "why": "Only the excluded test positions are held, so there is nothing to model."}
    rp, w, total, excluded = pr
    invested = sum(w.values())
    sim = simulate(rp, total, goals, drift, n, block, today=date.fromisoformat(close), invested=invested)
    bt = backtest_1y(rp, drift, block=block, invested=invested)
    if bt:  # check day t draws from prices up to panel row t and is judged on rows t..t + 252
        checks = bt.pop("checks")
        bt |= {"start": panel.index[checks[0]["day"]].strftime("%Y-%m-%d"),
               "end": panel.index[checks[-1]["day"] + YEAR].strftime("%Y-%m-%d")}
    rows = [ledger.make_row(close, "goal_1y", YEAR, sim["years"][0]["growth"], drift, w),
            ledger.make_row(close, f"goal_{goals.years}y", YEAR * goals.years, sim["years"][goals.years - 1]["growth"], drift, w)]
    if risk and risk.get("value"):
        rows.append(ledger.make_row(close, "risk_21d", risk["horizon_days"],
                                    {"0.025": risk["low"] / risk["value"] - 1, "0.975": risk["high"] / risk["value"] - 1}, None, w))
    summary = None
    if ledger_path is not None:
        if record:  # weights are today's: rows dated in the past would be hindsight
            ledger.record(ledger_path, rows)
        pending = {t for r in ledger.read(ledger_path) if r["scored"] is None for t in r["weights"]}
        ledger.score(ledger_path, score_panel(pending) if score_panel and pending else panel)
        summary = ledger.summary(ledger.read(ledger_path))
    return {"available": True, "close": close, "value": total, "excluded": excluded, "goals_file": goals.from_file,
            "history_start": panel.index[0].strftime("%Y-%m-%d"), "history_end": panel.index[-1].strftime("%Y-%m-%d"),
            "history_years": len(rp) / YEAR, "anchor": anchor, "backtest": bt, "ledger": summary, **sim}
