"""Analyst-based signals: buy and sell thresholds, status, size label, rating share, implied return.

Pure functions; the data comes from candidates.py. The rules are in the spec
docs/superpowers/specs/2026-11-18-search-and-signals-design.md.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

LARGE, MID = 10e9, 2e9  # market cap cut-offs in USD


def load_signal_config(path: str | Path = "config/signals.toml") -> dict:
    with open(path, "rb") as f:
        d = tomllib.load(f)
    return {"buy_margin": float(d["buy_margin"]), "thin_coverage": int(d["thin_coverage"])}


def thresholds(target_mean: float, margin: float) -> tuple[float, float]:
    """Buy below the price that leaves `margin` upside to the mean target; sell above the mean target."""
    return target_mean / (1 + margin), target_mean


def status(price: float, buy_below: float | None, sell_above: float | None, n_analysts: int, thin: int) -> str:
    if buy_below is None or sell_above is None or not n_analysts:
        return "no analyst coverage"
    if n_analysts < thin:
        return "thin coverage"
    if price <= buy_below:
        return "below buy threshold"
    if price >= sell_above:
        return "above sell threshold"
    return "between thresholds"


def size_label(market_cap: float | None) -> str | None:
    if not market_cap:
        return None
    return "large" if market_cap >= LARGE else "mid" if market_cap >= MID else "small"


def rating_share(counts: dict) -> float | None:
    """Share of strong buy and buy among all ratings."""
    total = sum(counts.get(k, 0) for k in ("strongBuy", "buy", "hold", "sell", "strongSell"))
    return (counts.get("strongBuy", 0) + counts.get("buy", 0)) / total if total else None


def implied_return(weights: dict[str, float], upside: dict[str, float | None]) -> tuple[float | None, float]:
    """Weighted analyst upside of the positions that have one, and the portfolio share they cover."""
    covered = {k: w for k, w in weights.items() if upside.get(k) is not None}
    share = sum(covered.values())
    if not share:
        return None, 0.0
    return sum(w * upside[k] for k, w in covered.items()) / share, share
