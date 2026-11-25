"""Portfolio risk in euros with today's weights held fixed, and what-if scenarios.

Methods as docs/mockups/src/analysis.py (and lovable-continuous src/lib/quant): sample covariance of
simple daily returns × 252, Euler risk shares, bad-day correlation on the worst fifth of portfolio days,
constant-weight replay for the worst fall and the past-year return.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

BAD_DAY_QUANTILE = 0.2


@dataclass
class PortfolioStats:
    vol: float
    beta: float
    worst: float
    ret: float
    tech: float
    enb: float
    total: float
    weights: dict[str, float]
    risk_share: dict[str, float]
    returns: pd.Series


def _returns(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.pct_change().iloc[1:]


def portfolio_stats(panel: pd.DataFrame, values: dict[str, float], cash: float, tech: set[str],
                    market: str = "SPY") -> PortfolioStats:
    R = _returns(panel)
    keys = list(values)
    total = sum(values.values()) + cash
    w = np.array([values[k] / total for k in keys])
    X = R[keys].to_numpy()
    rp = X @ w
    cov = np.atleast_2d(np.cov(X.T, ddof=1)) * 252
    vol = math.sqrt(float(w @ cov @ w))
    rc = w * (cov @ w) / vol**2 if vol > 0 else np.zeros_like(w)
    m = R[market].to_numpy()
    beta = float(np.cov(rp, m, ddof=1)[0, 1] / np.var(m, ddof=1))
    path = np.cumprod(1 + rp)
    worst = float(min(0.0, (path / np.maximum.accumulate(path) - 1).min()))
    enb = 1 / float(np.sum(np.append(w, cash / total) ** 2))
    return PortfolioStats(
        vol=vol, beta=beta, worst=worst, ret=float(path[-1] - 1),
        tech=sum(v for k, v in values.items() if k in tech) / total, enb=enb, total=total,
        weights=dict(zip(keys, w.tolist())), risk_share=dict(zip(keys, rc.tolist())),
        returns=pd.Series(rp, index=R.index),
    )


def asset_view(panel: pd.DataFrame, ticker: str, base: PortfolioStats) -> dict:
    x = _returns(panel)[ticker].to_numpy()
    rp = base.returns.to_numpy()
    rest = rp - base.weights.get(ticker, 0.0) * x
    bad = rp <= np.quantile(rp, BAD_DAY_QUANTILE)
    return {
        "vol": float(np.std(x, ddof=1) * math.sqrt(252)),
        "corr": float(np.corrcoef(x, rest)[0, 1]) if np.std(rest) > 1e-12 else None,  # no rest of portfolio: undefined
        "down": float(np.corrcoef(x[bad], rp[bad])[0, 1]),
        "beta_p": float(np.cov(x, rp, ddof=1)[0, 1] / np.var(rp, ddof=1)),
        "ret": float(np.prod(1 + x) - 1),
    }


def _summary(s: PortfolioStats) -> dict:
    return {k: getattr(s, k) for k in ("vol", "beta", "worst", "ret", "tech", "enb", "total", "weights")}


def add_scenario(panel: pd.DataFrame, values: dict[str, float], cash: float, tech: set[str],
                 ticker: str, amount: float) -> dict:
    """New money into one stock; existing positions unchanged."""
    v = dict(values)
    v[ticker] = v.get(ticker, 0.0) + amount
    s = portfolio_stats(panel, v, cash, tech)
    return {**_summary(s), "own_risk": s.risk_share[ticker]}


def sell_scenario(panel: pd.DataFrame, values: dict[str, float], cash: float, tech: set[str],
                  ticker: str) -> dict:
    """Sell one position and spread the proceeds pro rata over the other positions."""
    rest = {k: v for k, v in values.items() if k != ticker}
    scale = sum(values.values()) / sum(rest.values())
    s = portfolio_stats(panel, {k: v * scale for k, v in rest.items()}, cash, tech)
    return _summary(s)
