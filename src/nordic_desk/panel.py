"""Prices in euros on one weekday calendar, forward-filled, for portfolio risk."""
from __future__ import annotations

import pandas as pd


def to_eur(px: pd.Series, rate: pd.Series, currency: str) -> pd.Series:
    """Prices divided by the EUR rate of their currency (units per EUR, e.g. EURUSD=X), last known rate each date."""
    if currency == "EUR":
        return px
    fx = rate.reindex(rate.index.union(px.index)).sort_index().ffill().reindex(px.index)
    return px / fx


def eur_panel(series: dict[str, pd.Series], currency: dict[str, str], eurusd: pd.Series,
              end: str, n_returns: int | None = 252, rates: dict[str, pd.Series] | None = None) -> pd.DataFrame:
    end_ts = pd.Timestamp(end)
    cal = pd.DatetimeIndex(sorted(set().union(*(s.index for s in series.values()))))
    cal = cal[(cal <= end_ts) & (cal.day_of_week < 5)]
    cols = {}
    for t, s in series.items():
        c = currency[t]
        if c not in ("EUR", "USD") and c not in (rates or {}):
            raise ValueError(f"no EUR{c}=X rate for {t}")
        e = to_eur(s.sort_index(), eurusd if c == "USD" else (rates or {}).get(c), c)
        cols[t] = e.reindex(e.index.union(cal)).sort_index().ffill().reindex(cal)
    panel = pd.DataFrame(cols, index=cal)
    if n_returns is None:  # all dates where every series has a price
        return panel.dropna()
    panel = panel.iloc[-(n_returns + 1):]
    if len(panel) < n_returns + 1:
        raise ValueError(f"only {len(panel)} dates up to {end}, need {n_returns + 1}")
    missing = [t for t in panel.columns if panel[t].isna().any()]
    if missing:
        raise ValueError(f"no price at the window start {panel.index[0].date()} for: {', '.join(missing)}")
    return panel
