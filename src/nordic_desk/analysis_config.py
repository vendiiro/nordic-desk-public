"""Thresholds for the analysis page, read from config/analysis.toml."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass

from .quality import QualitySettings


@dataclass(frozen=True)
class EntryTh:
    pullback_pct_b: float = 0.2
    pullback_rsi: float = 40
    stretched_rsi: float = 70
    stretched_pct_b: float = 0.95
    trend_lookback: int = 21


@dataclass(frozen=True)
class LongTh:
    attractive_below: float = 0.30
    expensive_above: float = 0.70
    window_days: int = 1260
    min_days: int = 504
    eps_lag_days: int = 90
    big_3y: float = 1.0


@dataclass(frozen=True)
class GoalTh:
    drift: float = 0.07  # stated long-run yearly return in euros for the Goal page range; an assumption, not an estimate
    n_paths: int = 5000
    block: int = 21


@dataclass(frozen=True)
class AnalysisConfig:
    entry: EntryTh
    long: LongTh
    quality: QualitySettings
    goal: GoalTh = GoalTh()


def load(path: str = "config/analysis.toml") -> AnalysisConfig:
    with open(path, "rb") as f:
        d = tomllib.load(f)
    q = d.get("quality", {})
    return AnalysisConfig(EntryTh(**d.get("entry", {})), LongTh(**d.get("long", {})),
                          QualitySettings(**{**q, "must_pass": tuple(q.get("must_pass", ("net_margin_positive",)))}),
                          GoalTh(**d.get("goal", {})))
