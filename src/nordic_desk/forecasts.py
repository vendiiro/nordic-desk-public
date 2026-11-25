"""Forecasts data for the site: scorecard, lump vs spread and realistic targets, from local caches only."""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from . import fundamentals, history, ohlc, prices
from .analysis_config import load as load_cfg
from .config import load_instruments
from .eur import asof, currency_of, eur_closes, quote_ok
from .expected import anchor, combine, signal_piece
from .lumpspread import lump_vs_spread, volsized
from .volsize import suggestion
from .scorecard import GOOD, LABELS, group_stats, samples, stock_reading, verdict_series
from .targets import check, monthly_snapshots, per_ticker, rates, realistic

HORIZONS = (63, 126, 252)
SPREADS = (3, 6, 12)
WARNING = ("Stocks are the ones you hold or watch today; past winners are over-represented, "
           "so these numbers flatter the signals.")


def clean(x):
    """JSON-safe copy: non-finite floats become None, numpy scalars become Python ones."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return float(x) if math.isfinite(x) else None
    return x


def build_forecasts(subs, desk: dict, cards_doc: dict | None, price_root, ohlc_root, fund_root, hist_path, instruments_path) -> dict:
    cfg = load_cfg()
    inst = load_instruments(instruments_path) if Path(instruments_path).exists() else {}
    eurusd = prices.load("EURUSD=X", price_root)
    spy = prices.load("SPY", price_root)
    spy_eur = spy / asof(eurusd, spy.index)
    excluded, used, frames, today = [], {}, {H: [] for H in HORIZONS}, {}
    for s in subs:
        f = fundamentals.load_fundamentals(s.ticker, fund_root)
        if not quote_ok(f):
            qt = (f or {}).get("quote_type")
            excluded.append({"ticker": s.ticker, "why": "price index (no dividends, can't be bought)" if qt == "INDEX"
                             else "crypto" if qt == "CRYPTOCURRENCY" else "no company data yet"})
            continue
        cur = currency_of(s.ticker, fund_root, inst)
        c_eur = eur_closes(prices.load(s.ticker, price_root), cur, eurusd)
        o = ohlc.load_ohlc(s.ticker, ohlc_root)
        if c_eur is None or c_eur.dropna().empty or o.empty:
            excluded.append({"ticker": s.ticker, "why": f"quoted in {cur}, only USD and EUR are compared" if c_eur is None and cur
                             else "no price history"})
            continue
        used[s.ticker] = c_eur
        groups = verdict_series(o, cfg.entry)
        today[s.ticker] = {"group": groups.iloc[-1], "date": groups.index[-1].strftime("%Y-%m-%d")}
        for H in HORIZONS:
            frames[H].append(samples(groups, c_eur, spy_eur, H).assign(ticker=s.ticker))
    scorecard = {}
    for H in HORIZONS:
        df = pd.concat(frames[H]) if frames[H] else pd.DataFrame(columns=["date", "month", "group", "excess", "beat", "ticker"])
        pooled = {g: {**group_stats(df[df.group == g], H, g in GOOD), "label": LABELS[g]} for g in LABELS if (df.group == g).any()}
        per_stock = {}
        for t in used:
            rows = df[df.ticker == t]
            per_stock[t] = {}
            for g in LABELS:
                st = group_stats(rows[rows.group == g], H, g in GOOD) if (rows.group == g).any() else None
                if st:
                    per_stock[t][g] = {**st, "reading": stock_reading(st, pooled.get(g, {}).get("reading", ""), g in GOOD),
                                       "label": LABELS[g], "since": str(rows[rows.group == g].date.min().year)}
        scorecard[str(H)] = {"groups": pooled, "per_stock": per_stock}
    lump = {t: {str(k): lump_vs_spread(c, k) for k in SPREADS} for t, c in {**used, "SPY": spy_eur}.items()}
    snaps = monthly_snapshots(history._read(hist_path))
    checked = check(snaps, lambda t: ohlc.load_ohlc(t, ohlc_root)["close"])
    r = rates(checked, snaps[0]["date"] if snaps else None)
    counts = per_ticker(checked)
    cards = (cards_doc or {}).get("cards") or {}
    trows = []
    for c in (cards.values() if isinstance(cards, dict) else cards):
        a = c.get("analysts") or {}
        tm, up = a.get("target_mean"), a.get("upside")
        if tm and up is not None:
            trows.append({"ticker": c["ticker"], "name": c.get("name") or c["ticker"], "currency": c.get("currency"), "price": tm / (1 + up), "target": tm,
                          "upside": up, "realistic": realistic(up, r["overshoot"]), "record": counts.get(c["ticker"], 0)})
    anc = anchor(spy_eur)
    upside = {x["ticker"]: x["realistic"] for x in trows}
    expected = ({t: combine(anc["rate"], upside.get(t), signal_piece(anc["rate"], today[t]["group"], scorecard["252"]["groups"]))
                 for t in used} if anc else {})
    vols = {t: {"now": suggestion(c), **{str(k): volsized(c, k) for k in SPREADS}} for t, c in {**used, "SPY": spy_eur}.items()}
    return clean({"built": date.today().isoformat(), "excluded": excluded, "warning": WARNING, "scorecard": scorecard, "today": today,
                  "anchor": anc, "expected": expected, "volsize": vols,
                  "risk": (desk.get("forecast") or {}).get("backtest"), "targets": {"rates": r, "rows": trows}, "lump": lump,
                  "subjects": [{"ticker": s.ticker, "name": s.name, "groups": list(s.groups)} for s in subs if s.ticker in used]})


def write_forecasts(out_dir: Path, subs, desk: dict, cards_doc: dict | None, price_root=None, ohlc_root=None, fund_root=None,
                    hist_path=None, instruments_path="config/instruments.toml") -> dict:
    d = build_forecasts(subs, desk, cards_doc, price_root or prices.ROOT, ohlc_root or ohlc.ROOT, fund_root or fundamentals.ROOT,
                        hist_path or history.PATH, instruments_path)
    (Path(out_dir) / "forecasts.json").write_text(json.dumps(d, allow_nan=False), encoding="utf-8")
    return d
