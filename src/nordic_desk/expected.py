"""Combined 12-month expected return: equal blend of the available pieces, pulled halfway toward a market anchor
(Rapach, Strauss & Zhou 2010: simple combinations beat single predictors out of sample)."""
from __future__ import annotations

import pandas as pd

EVIDENCE = ("helps", "works against")


def anchor(spy_eur: pd.Series) -> dict | None:
    """SPY's annualised total return in euros over the stored history."""
    s = spy_eur.dropna()
    if len(s) < 253:
        return None
    rate = (s.iloc[-1] / s.iloc[0]) ** (252 / (len(s) - 1)) - 1
    return {"rate": float(rate), "from": str(s.index[0].year), "to": str(s.index[-1].year)}


def signal_piece(anchor_rate: float, group: str | None, pooled252: dict) -> float | None:
    """Anchor plus how today's verdict group did against SPY over 12 months, only when that history points one way."""
    g = pooled252.get(group) if group else None
    if not g or g.get("reading") not in EVIDENCE or g.get("mean") is None:
        return None
    return anchor_rate + g["mean"]


def combine(anchor_rate: float, analyst: float | None, signal: float | None) -> dict:
    pieces = [p for p in (analyst, signal) if p is not None]
    combined = anchor_rate if not pieces else 0.5 * anchor_rate + 0.5 * sum(pieces) / len(pieces)
    return {"anchor": anchor_rate, "analyst": analyst, "signal": signal, "combined": combined, "pieces": len(pieces)}
