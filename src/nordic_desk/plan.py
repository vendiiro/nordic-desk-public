"""Split new money over the ideas: each step goes to the idea that lowers portfolio volatility most,
without taking the technology share above the cap (config/target.toml).

shortcut: greedy steps on the past year's covariance, not a full optimiser; good enough for a few thousand euros.
"""
from __future__ import annotations

import pandas as pd

from .risk import add_scenario, portfolio_stats

KEYS = ("vol", "beta", "worst", "tech", "enb")


def plan_allocation(panel: pd.DataFrame, values: dict[str, float], cash: float, tech: set[str], candidates: list[str],
                    amount: float, step: float, tech_max: float) -> dict:
    v, split = dict(values), {}
    before = portfolio_stats(panel, v, cash, tech)
    note = ""
    for _ in range(int(amount // step)):
        best = None
        for c in candidates:
            s = add_scenario(panel, v, cash, tech, c, step)
            if c in tech and s["tech"] > tech_max:
                continue  # would push the technology share over the cap
            if best is None or s["vol"] < best[1]["vol"]:
                best = (c, s)
        if best is None:
            note = f"every idea would take the technology share above the {tech_max:.0%} cap"
            break
        c = best[0]
        v[c] = v.get(c, 0.0) + step
        split[c] = split.get(c, 0.0) + step
    after = portfolio_stats(panel, v, cash, tech)
    return {"split": split, "note": note, "amount": amount, "tech_max": tech_max,
            "before": {k: getattr(before, k) for k in KEYS}, "after": {k: getattr(after, k) for k in KEYS}}


def optimise_allocation(panel: pd.DataFrame, values: dict[str, float], cash: float, tech: set[str], candidates: list[str],
                        amount: float, tech_max: float) -> dict:
    """Minimum-variance split of new money (SLSQP), technology share at or under the cap where it can be reached."""
    import numpy as np
    from scipy.optimize import minimize

    keys = list(dict.fromkeys(list(values) + candidates))
    X = panel[keys].pct_change().iloc[1:].to_numpy()
    cov = np.atleast_2d(np.cov(X.T, ddof=1)) * 252
    total = sum(values.values()) + cash + amount
    v = np.array([values.get(k, 0.0) for k in keys])
    idx = np.array([keys.index(c) for c in candidates])
    is_tech = np.array([c in tech for c in candidates])
    tech_now = sum(x for k, x in values.items() if k in tech)
    reach = (tech_now + (0.0 if (~is_tech).any() else amount)) / total
    cap = max(tech_max, reach)

    def weights(y):  # y: share of the new money per candidate, so the solver works on numbers near 1
        w = v.copy()
        w[idx] += y * amount
        return w / total

    var = lambda y: 1e4 * weights(y) @ cov @ weights(y)  # variance in percent squared: a slope the solver can see
    grad = lambda y: 1e4 * 2 * amount / total * (cov @ weights(y))[idx]
    res = minimize(var, np.full(len(candidates), 1 / len(candidates)), jac=grad, method="SLSQP",
                   bounds=[(0, 1)] * len(candidates), options={"ftol": 1e-12, "maxiter": 500},
                   constraints=[{"type": "eq", "fun": lambda y: y.sum() - 1},
                                {"type": "ineq", "fun": lambda y: cap - (tech_now + amount * y[is_tech].sum()) / total}])
    split = {c: round(float(y * amount), 0) for c, y in zip(candidates, res.x) if y * amount >= 1}
    if split:  # rounding to whole euros: give the remainder to the largest amount so the split adds up
        top = max(split, key=split.get)
        split[top] += amount - sum(split.values())
    after_vals = dict(values)
    for c, x in split.items():
        after_vals[c] = after_vals.get(c, 0.0) + x
    before, after = portfolio_stats(panel, values, cash, tech), portfolio_stats(panel, after_vals, cash, tech)
    note = "" if cap == tech_max else f"the {tech_max:.0%} technology cap cannot be reached with this amount"
    return {"split": split, "note": note if res.success else f"optimiser: {res.message}", "amount": amount, "tech_max": tech_max,
            "before": {k: getattr(before, k) for k in KEYS}, "after": {k: getattr(after, k) for k in KEYS}}


def run_plan(amount: float, ideas: list[str], info: dict[str, dict], out_dir=None, price_root=None,
             holdings_path: str = "config/holdings.local.toml", end: str | None = None, target_path: str = "config/target.toml") -> dict:
    """Plan new money over `ideas` (info: ticker -> {currency, sector} from the candidate cache) and write out/plan.json."""
    import json
    import tomllib
    from pathlib import Path

    from . import prices
    from .build import last_full_close
    from .config import load_holdings, load_instruments, load_tech
    from .panel import eur_panel

    out_dir, price_root = Path(out_dir or "out"), Path(price_root or prices.ROOT)
    with open(target_path, "rb") as f:
        cfg = tomllib.load(f)
    load = lambda t: prices.load(t, root=price_root)
    end = end or last_full_close(load("SPY"))
    cut = lambda s: s[s.index <= pd.Timestamp(end)]
    h = load_holdings(holdings_path)
    inst = load_instruments()
    cur = {i.ticker: i.currency for i in inst.values()}
    tech = {i.ticker for i in inst.values() if i.tech} | set(load_tech())
    values: dict[str, float] = {}
    for p in h.positions:
        if p.ticker:
            values[p.ticker] = values.get(p.ticker, 0.0) + p.value_eur
    cash = h.cash_eur + sum(p.value_eur for p in h.positions if not p.ticker)
    ok = [t for t in ideas if t not in values and (info.get(t, {}).get("currency") in ("USD", "EUR")) and len(cut(load(t))) >= 254]
    tech |= {t for t in ok if info[t].get("sector") == "Technology"}
    tickers = list(dict.fromkeys(list(values) + ok + ["SPY"]))
    ccy = {t: cur.get(t, info.get(t, {}).get("currency") or "USD") for t in tickers} | {"SPY": "USD"}
    panel = eur_panel({t: cut(load(t)) for t in tickers}, ccy, cut(load("EURUSD=X")), end)
    out = plan_allocation(panel, values, cash, tech, ok, amount, float(cfg["step"]), float(cfg["tech_max"]))
    out["optimised"] = optimise_allocation(panel, values, cash, tech, ok, amount, float(cfg["tech_max"]))
    out |= {"skipped": [t for t in ideas if t not in ok and t not in values], "close": end}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plan.json").write_text(json.dumps(out, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return out
