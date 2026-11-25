"""Next-month risk of the portfolio: EWMA volatility (RiskMetrics, lambda 0.94), a 95% value range,
and a calibration check of the one-day 95% line over all common history (Kupiec test).

shortcut: EWMA only; GARCH-t, block bootstrap and regime switching need an optimiser (scipy or arch), add them then.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

LAMBDA, Z95, WARMUP = 0.94, 1.645, 60


def ewma_sigma(r, lam: float = LAMBDA) -> np.ndarray:
    """sigma[t] is the forecast for day t made with returns before t; the last value forecasts the next day."""
    r = np.asarray(r, dtype=float)
    var = np.empty(len(r) + 1)
    var[0] = np.var(r[:WARMUP]) if len(r) >= WARMUP else np.var(r)
    for t, x in enumerate(r):
        var[t + 1] = lam * var[t] + (1 - lam) * x * x
    return np.sqrt(var)


def var_backtest(r, sigma, p: float = 0.05) -> dict:
    """How often a day lost more than the one-day 95% line; Kupiec p-value for 'the rate is 5%'."""
    r, sigma = np.asarray(r), np.asarray(sigma)[: len(r)]
    hits = int(np.sum(r < -Z95 * sigma))
    n = len(r)
    rate = hits / n
    lr = -2 * ((n - hits) * math.log(1 - p) + hits * math.log(p))
    if 0 < hits < n:
        lr += 2 * ((n - hits) * math.log(1 - rate) + hits * math.log(rate))
    return {"n": n, "hits": hits, "rate": rate, "expected": p, "p_value": math.erfc(math.sqrt(max(lr, 0) / 2))}


# ---- more models: GARCH(1,1)-t, Markov switching variance, block bootstrap (spec 2026-11-19-risk-models) ----
MODELS = ("ewma", "garch", "bootstrap", "regime")
REFIT, MIN_TRAIN, HS_WINDOW, BLOCK = 21, 504, 500, 10


def _garch_fit(r):
    from arch import arch_model

    return arch_model(np.asarray(r) * 100, mean="Zero", vol="GARCH", p=1, q=1, dist="t").fit(disp="off", show_warning=False)


def _t_line(nu: float) -> float:
    """5% quantile of a unit-variance Student-t."""
    from scipy.stats import t

    return float(t.ppf(0.05, nu) * math.sqrt((nu - 2) / nu))


def garch_t_sigma(r) -> tuple[float, dict]:
    res = _garch_fit(r)
    var = res.forecast(horizon=1, reindex=False).variance.to_numpy()[-1, 0]
    return math.sqrt(var) / 100, {k: float(v) for k, v in res.params.items()}


def _regime_model(r):
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    return MarkovRegression(np.asarray(r) * 100, k_regimes=2, trend="c", switching_variance=True)


def _sig2(res) -> np.ndarray:
    """Regime variances in return units (params come back as a plain array)."""
    p = dict(zip(res.model.param_names, np.asarray(res.params)))
    return np.array([p["sigma2[0]"], p["sigma2[1]"]]) / 1e4


def _regime_next(res) -> tuple[float, float, float, float]:
    sig = np.sqrt(_sig2(res))
    hi = int(np.argmax(sig))
    p_next = res.regime_transition[:, :, -1] @ res.filtered_marginal_probabilities[-1]  # P[i, j] = P(S_t=i | S_t-1=j)
    return float(math.sqrt(p_next @ sig**2)), float(p_next[hi]), float(sig[1 - hi]), float(sig[hi])


def regime_sigma(r) -> tuple[float, float, float, float]:
    """Next-day sigma mixing the two regimes, probability of the high-volatility regime, and both regime sigmas."""
    return _regime_next(_regime_model(r).fit(disp=False))


def bootstrap_range(r, horizon: int = 21, block: int = BLOCK, n: int = 5000, seed: int = 0, q=(0.05, 0.95)) -> tuple[float, float]:
    """Quantiles of the horizon's log return, from blocks of past days drawn with replacement."""
    lr = np.log1p(np.asarray(r))
    rng = np.random.default_rng(seed)
    k = -(-horizon // block)
    if len(lr) <= block:
        raise ValueError("too few days for a block bootstrap")
    starts = rng.integers(0, len(lr) - block + 1, size=(n, k))
    paths = lr[starts[..., None] + np.arange(block)].reshape(n, -1)[:, :horizon].sum(axis=1)
    return float(np.quantile(paths, q[0])), float(np.quantile(paths, q[1]))


def rolling_lines(r, model: str, refit: int = REFIT, min_train: int = MIN_TRAIN) -> np.ndarray:
    """One-day 95% loss line (a negative return) for each day from min_train on, using only earlier days."""
    r = np.asarray(r, dtype=float)
    n = len(r)
    if model == "ewma":
        return -Z95 * ewma_sigma(r)[min_train:n]
    if model == "bootstrap":
        return np.array([np.quantile(r[max(0, t - HS_WINDOW):t], 0.05) for t in range(min_train, n)])
    out = []
    for k in range(min_train, n, refit):
        end = min(k + refit, n)
        if model == "garch":
            from arch import arch_model

            p = _garch_fit(r[:k]).params
            vol = arch_model(r[:end] * 100, mean="Zero", vol="GARCH", p=1, q=1, dist="t").fix(p).conditional_volatility / 100
            out.extend(np.asarray(vol)[k:end] * _t_line(float(p["nu"])))
        else:
            res = _regime_model(r[:k]).fit(disp=False)
            filt = _regime_model(r[:end]).filter(res.params)
            sig2 = _sig2(res)
            P = filt.regime_transition[:, :, -1]
            fp = filt.filtered_marginal_probabilities
            for t in range(k, end):  # predicted regime for day t from information up to t-1
                out.append(-Z95 * math.sqrt((P @ fp[t - 1]) @ sig2))
    return np.array(out)


def christoffersen(hits) -> float:
    """p-value that breaches are independent from one day to the next (no clustering)."""
    h = np.asarray(hits, dtype=int)
    a, b = h[:-1], h[1:]
    n00, n01 = int(np.sum((a == 0) & (b == 0))), int(np.sum((a == 0) & (b == 1)))
    n10, n11 = int(np.sum((a == 1) & (b == 0))), int(np.sum((a == 1) & (b == 1)))
    ll = lambda k, n, p: (k * math.log(p) if k else 0.0) + ((n - k) * math.log(1 - p) if n - k else 0.0)
    p01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    p11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    p = (n01 + n11) / max(len(a), 1)
    if p in (0.0, 1.0):
        return 1.0
    lr = -2 * (ll(n01 + n11, len(a), p) - ll(n01, n00 + n01, p01 or 1e-12) - ll(n11, n10 + n11, p11 or 1e-12))
    return math.erfc(math.sqrt(max(lr, 0.0) / 2))


def calibrate(r, min_train: int = MIN_TRAIN) -> dict:
    r = np.asarray(r, dtype=float)
    out = {}
    for m in MODELS:
        try:
            line = rolling_lines(r, m, min_train=min_train)
        except Exception:
            continue
        hits = r[min_train:] < line
        out[m] = {"n": int(len(hits)), "hits": int(hits.sum()), "rate": float(hits.mean()),
                  "kupiec_p": _kupiec(int(hits.sum()), len(hits)), "christoffersen_p": christoffersen(hits)}
    return out


def _kupiec(x: int, n: int, p: float = 0.05) -> float:
    lr = -2 * ((n - x) * math.log(1 - p) + x * math.log(p))
    if 0 < x < n:
        lr += 2 * ((n - x) * math.log(1 - x / n) + x * math.log(x / n))
    return math.erfc(math.sqrt(max(lr, 0) / 2))


LABELS = {"ewma": "EWMA", "garch": "GARCH-t", "bootstrap": "Bootstrap, last 500 days", "regime": "Markov regimes"}
EXCLUDE = ("CBUT.DE", "ETH-EUR")  # the owner's crypto test positions: counted as cash in the models
CACHE = "data/forecast_cache.json"


def portfolio_forecast(panel: pd.DataFrame, values: dict[str, float], cash: float, horizon: int = 21,
                       cache_path=CACHE, today: str | None = None) -> dict:
    """All four models on the portfolio's daily returns in euros (today's weights fixed); headline = best calibrated."""
    import datetime as _dt
    import json
    from pathlib import Path

    excluded = [t for t in values if t in EXCLUDE]
    model_vals = {t: v for t, v in values.items() if t not in EXCLUDE}
    if not model_vals:
        return None
    total = sum(values.values()) + cash
    w = np.array([model_vals[t] / total for t in model_vals])
    rp = panel[list(model_vals)].pct_change().iloc[1:].to_numpy() @ w
    rng95 = lambda s: (float(total * math.exp(-1.96 * s * math.sqrt(horizon))), float(total * math.exp(1.96 * s * math.sqrt(horizon))))
    ranges, failed, regime = {}, [], None
    s_ewma = float(ewma_sigma(rp)[-1])
    ranges["ewma"] = (s_ewma, *rng95(s_ewma))
    try:
        s_garch, _ = garch_t_sigma(rp)
        ranges["garch"] = (s_garch, *rng95(s_garch))
    except Exception:
        failed.append("garch")
    try:
        s_reg, p_high, s_lo, s_hi = regime_sigma(rp)
        ranges["regime"] = (s_reg, *rng95(s_reg))
        regime = {"p_high": p_high, "sigma_low": s_lo, "sigma_high": s_hi}
    except Exception:
        failed.append("regime")
    try:  # same 500-day window as its calibration, so the range and the check describe one model
        b_lo, b_hi = bootstrap_range(rp[-HS_WINDOW:], horizon, q=(0.025, 0.975))
        sig_b = (b_hi - b_lo) / (2 * 1.96 * math.sqrt(horizon))
        ranges["bootstrap"] = (sig_b, float(total * math.exp(b_lo)), float(total * math.exp(b_hi)))
    except Exception:
        failed.append("bootstrap")
    base = {"horizon_days": horizon, "value": float(total), "excluded": excluded, "failed": failed, "regime": regime,
            "history_start": panel.index[0].strftime("%Y-%m-%d")}

    if len(rp) < MIN_TRAIN + REFIT:  # under about two years: nothing to check the models against
        models = {m: {"label": LABELS[m], "sigma_daily": s, "vol_ann": s * math.sqrt(252), "low": lo, "high": hi, "calibration": None}
                  for m, (s, lo, hi) in ranges.items()}
        h = models["ewma"]
        return base | {"headline": "ewma", "models": models, "sigma_daily": h["sigma_daily"], "vol_ann": h["vol_ann"],
                       "low": h["low"], "high": h["high"], "backtest": None}
    day = _dt.date.fromisoformat(today) if today else _dt.date.today()
    # weights rounded to whole percents: daily price moves keep the key; a version tag clears entries when the models change
    key = f"v2|{day.isocalendar()[0]}-W{day.isocalendar()[1]}|" + json.dumps({t: round(x, 2) for t, x in zip(model_vals, w)}, sort_keys=True)
    path = Path(cache_path) if cache_path else None
    cache = json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else {}
    if key not in cache:
        cache = {key: calibrate(rp)}  # one entry: older weeks are not needed
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache), encoding="utf-8")
    calib = cache[key]
    start = panel.index[1 + MIN_TRAIN].strftime("%Y-%m-%d")
    models = {m: {"label": LABELS[m], "sigma_daily": s, "vol_ann": s * math.sqrt(252), "low": lo, "high": hi,
                  "calibration": (calib[m] | {"start": start}) if m in calib else None}
              for m, (s, lo, hi) in ranges.items()}
    checked = [m for m in models if models[m]["calibration"]] or ["ewma"]
    headline = max(checked, key=lambda m: min(calib[m]["kupiec_p"], calib[m]["christoffersen_p"]) if m in calib else -1)
    h, c = models[headline], models[headline]["calibration"]
    return base | {"headline": headline, "models": models, "sigma_daily": h["sigma_daily"], "vol_ann": h["vol_ann"],
                   "low": h["low"], "high": h["high"],
                   "backtest": {"n": c["n"], "hits": c["hits"], "rate": c["rate"], "expected": 0.05, "p_value": c["kupiec_p"],
                                "christoffersen_p": c["christoffersen_p"], "start": start} if c else None}
