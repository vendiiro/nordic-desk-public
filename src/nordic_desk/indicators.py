"""Chart indicators for the analysis page, computed once in Python (the page only draws them)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analysis_config import LongTh


def _rsi(c: pd.Series) -> pd.Series:
    """Wilder RSI(14). NaN while too short or when the price never moved; 100 with no losses."""
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + up / dn)
    r[(dn == 0) & (up > 0)] = 100.0
    r[(dn == 0) & (up == 0)] = np.nan
    r.iloc[:15] = np.nan
    return r


def compute(ohlc: pd.DataFrame, trend_lookback: int = 21) -> pd.DataFrame:
    c = ohlc["close"].astype(float)
    out = pd.DataFrame(index=ohlc.index)
    for k in ("close", "open", "high", "low"):
        out[k] = ohlc[k].astype(float)
    out["sma50"] = c.rolling(50).mean()
    s200 = c.rolling(200).mean()
    out["sma200"] = s200
    out["dist200"] = c / s200 - 1
    prev = s200.shift(trend_lookback)
    out["trend"] = [None if np.isnan(s) or np.isnan(p) else "up" if x > s and s > p else "down" if x < s and s < p else "mixed"
                    for x, s, p in zip(c, s200, prev)]
    mid, sd = c.rolling(20).mean(), c.rolling(20).std(ddof=0)
    out["bb_mid"], out["bb_up"], out["bb_lo"] = mid, mid + 2 * sd, mid - 2 * sd
    width = out["bb_up"] - out["bb_lo"]
    out["pct_b"] = ((c - out["bb_lo"]) / width).where(width > 0)
    out["rsi"] = _rsi(c)
    ema = lambda n: c.ewm(span=n, adjust=False).mean()
    out["macd"] = ema(12) - ema(26)
    out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    out["drawdown"] = c / c.cummax() - 1
    hi = ohlc["high"].astype(float)
    hi = c if hi.isna().all() else hi.fillna(c)
    out["high52"] = hi.rolling(252, min_periods=1).max()
    out["dist52"] = c / out["high52"] - 1
    out["vol"] = np.log(c).diff().rolling(63).std() * np.sqrt(252)
    out["mom"] = c.shift(21) / c.shift(252) - 1
    out["ret3y"] = c / c.shift(756) - 1
    for k, n in (("chg_1w", 5), ("chg_1m", 21), ("chg_1y", 252)):
        out[k] = c / c.shift(n) - 1
    return out


def pe_frame(close: pd.Series, eps_avail: list[tuple[pd.Timestamp, float]], th: LongTh) -> pd.DataFrame:
    """Point-in-time P/E: each day uses the latest EPS already public, and its own trailing window only."""
    c = close.astype(float)
    eps = pd.Series(np.nan, index=c.index)
    if eps_avail:
        dates = pd.DatetimeIndex([d for d, _ in eps_avail])
        vals = np.array([v for _, v in eps_avail], dtype=float)
        pos = dates.searchsorted(c.index, side="right") - 1
        eps = pd.Series(np.where(pos >= 0, vals[np.clip(pos, 0, None)], np.nan), index=c.index)
    pe = (c / eps).where(eps > 0)
    roll = pe.rolling(th.window_days, min_periods=1)

    def pct(w: np.ndarray) -> float:
        last = w[-1]
        ok = w[~np.isnan(w)]
        return np.nan if np.isnan(last) else float((ok <= last).sum() / len(ok))

    return pd.DataFrame({"pe": pe, "pe_pct": roll.apply(pct, raw=True), "pe_median": roll.median(), "pe_n": roll.count()})
