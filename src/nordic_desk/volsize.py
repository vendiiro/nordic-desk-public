"""Volatility-sized purchases: put less in now when a stock is far jumpier than usual (Moreira & Muir 2017, on factor
portfolios; for single purchases it is a heuristic, which the lump planner tests on history)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

MIN_OBS = 252  # a year of 63-day volatility readings before "usual" means anything
FLOOR = 0.25
DEAD_BAND = 0.8  # hold back only when at least a fifth would wait: smaller bumps in volatility are noise


def vol63(close: pd.Series) -> pd.Series:
    """Annualised 63-day volatility of daily log returns (same definition as indicators.compute)."""
    return np.log(close).diff().rolling(63).std() * np.sqrt(252)


def usual_series(vol: pd.Series) -> pd.Series:
    """Median volatility over all days up to each day: point in time."""
    return vol.expanding(min_periods=MIN_OBS).median()


def first_part(current: float, usual: float) -> float:
    if not (current and usual) or math.isnan(current) or math.isnan(usual) or current <= 0:
        return 1.0
    f = (usual / current) ** 2
    return 1.0 if f >= DEAD_BAND else float(max(FLOOR, f))


def suggestion(close_eur: pd.Series) -> dict | None:
    c = close_eur.dropna()
    v = vol63(c)
    u = usual_series(v)
    if c.empty or math.isnan(u.iloc[-1]) or math.isnan(v.iloc[-1]):
        return None
    return {"current": float(v.iloc[-1]), "usual": float(u.iloc[-1]), "first": first_part(float(v.iloc[-1]), float(u.iloc[-1]))}
