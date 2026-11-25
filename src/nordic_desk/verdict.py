"""Rules-based verdicts for the analysis page. Fixed rules on the readings, no AI; thresholds from config/analysis.toml."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .analysis_config import EntryTh, LongTh
from .fundamentals import PE_REASONS
from .quality import QualityResult, QualitySettings, fails

NOT_ENOUGH = ("Wait", "wait", "Not enough history yet")
STRETCHED = ("Stretched", "str", "Far above its recent range; evidence that a dip follows is weak")
PULLBACK = ("Good entry", "good", "Pullback inside an uptrend")
STEADY = ("Good entry", "good", "Steady uptrend, nothing stretched")
DOWN = ("Wait", "wait", "Trend is down")
MIXED = ("Wait", "wait", "No clear trend yet")
NO_PE = ("Not enough history", "neu", "Not enough P/E history")
NO_PE_WHY = {r: ("Not enough history", "neu", f"P/E not available: {r}") for r in PE_REASONS}
LONG_QUALITY = {"Attractive": ("Attractive", "good", "Quality business at a below-normal price"),
                "Fair": ("Fair", "neu", "Quality business at a normal price"),
                "Expensive": ("Expensive", "str", "Good business, but priced above its own history")}
LONG_PLAIN = {"Attractive": ("Attractive", "good", "Below its normal price"),
              "Fair": ("Fair", "neu", "Normal price"),
              "Expensive": ("Expensive", "str", "Above its normal price")}
VERDICT_TABLE: list[tuple[str, str, str]] = [NOT_ENOUGH, STRETCHED, PULLBACK, STEADY, DOWN, MIXED, NO_PE, *NO_PE_WHY.values(),
                                             *LONG_QUALITY.values(), *LONG_PLAIN.values()]


@dataclass(frozen=True)
class Verdict:
    v: str
    cls: str
    line: str
    why: tuple[tuple[str, str], ...]


def _p(x: float, d: int = 0) -> str:
    return f"{x:+.{d}%}".replace("-", "−")


def _none(x) -> bool:
    return x is None or x != x  # None or NaN


def entry_verdict(r: Mapping, th: EntryTh) -> Verdict:
    t, pb, rsi, mom, d52 = (r.get(k) for k in ("trend", "pct_b", "rsi", "mom", "dist52"))
    if any(_none(x) for x in (t, pb, rsi)):
        return Verdict(*NOT_ENOUGH, ())
    why = [("+" if t == "up" else "–", "Above a rising 200-day line: long-term uptrend" if t == "up"
            else "Below a falling 200-day line: downtrend" if t == "down" else "Around the 200-day line: no clear trend"),
           ("+" if pb < th.pullback_pct_b else "–" if pb > th.stretched_pct_b else "·",
            "Near the lower Bollinger band: short-term dip" if pb < th.pullback_pct_b
            else "Near the upper Bollinger band: short-term stretched" if pb > th.stretched_pct_b
            else "Near the upper Bollinger band, not yet stretched" if pb > 0.9 else "Inside the Bollinger bands: normal range"),
           ("+" if rsi < th.pullback_rsi else "–" if rsi > th.stretched_rsi else "·",
            f"RSI {rsi:.1f}: " + ("oversold" if rsi < 30 else "weak, cooling off" if rsi < th.pullback_rsi
                                  else "overbought" if rsi > th.stretched_rsi else "neutral"))]
    if not _none(mom):
        why.append(("+" if mom > 0 else "–", f"12-1 momentum {_p(mom)}: " + ("winners tend to keep winning for months" if mom > 0
                                                                              else "recent loser, momentum against you")))
    if not _none(d52):
        why.append(("+" if d52 > -0.1 else "·", f"{_p(d52)} from 52-week high"))
    if rsi > th.stretched_rsi or pb > th.stretched_pct_b:
        row = STRETCHED
    elif t == "up" and (pb < th.pullback_pct_b or rsi < th.pullback_rsi):
        row = PULLBACK
    elif t == "up" and not _none(mom) and mom > 0:
        row = STEADY
    else:
        row = DOWN if t == "down" else MIXED
    return Verdict(*row, tuple(why))


def long_verdict(r: Mapping, kind: str, q: QualityResult | None, qs: QualitySettings, th: LongTh, today: bool) -> Verdict | None:
    if kind != "stock":
        return None
    pe, pct, med, n, r3, vol, dd = (r.get(k) for k in ("pe", "pe_pct", "pe_median", "pe_n", "ret3y", "vol", "worst_dd"))
    why: list[tuple[str, str]] = []
    if _none(pe) or _none(pct) or _none(n) or n < th.min_days:
        band = None
    else:
        band = "Attractive" if pct < th.attractive_below else "Expensive" if pct > th.expensive_above else "Fair"
        why.append(("+" if band == "Attractive" else "–" if band == "Expensive" else "·",
                    f"P/E {pe:.1f} vs its median {med:.1f}: cheaper than {round((1 - pct) * 100)}% of days in the window"))
    failed = None
    if not today:
        why.append(("·", "quality: today's snapshot, not used for past days"))
    elif q is None or (failed := fails(q, qs)) is None:
        why.append(("·", f"Quality could not be judged ({q.status if q else 'no data'})"))
    elif failed:
        broken = [c["label"] for c in q.checks if c["ok"] is False] + list(q.must_failed)
        why.append(("–", "Quality checks fail: " + ", ".join(broken)))
    else:
        why.append(("+", f"Quality passes (score {q.score})"))
    if not _none(r3):
        why.append(("–" if r3 > th.big_3y else "·", f"3-year return {_p(r3)}"
                    + (": big long-run winners tend to cool" if r3 > th.big_3y else "")))
    if not _none(vol) and not _none(dd):
        why.append(("·", f"Expect swings of about {vol:.0%} a year; worst fall in the window {_p(dd)}"))
    if band is None:
        return Verdict(*NO_PE_WHY.get(r.get("pe_reason"), NO_PE), tuple(why))
    if failed and band == "Attractive":
        band = "Fair"
    return Verdict(*(LONG_QUALITY if today and failed is False else LONG_PLAIN)[band], tuple(why))
