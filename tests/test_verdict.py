import itertools
import re

import pytest

from nordic_desk.analysis_config import EntryTh, LongTh
from nordic_desk.quality import QualitySettings, quality_detail
from nordic_desk.verdict import VERDICT_TABLE, entry_verdict, long_verdict

E, L, QS = EntryTh(), LongTh(), QualitySettings(market_cap_min=1e9)
UP = {"trend": "up", "pct_b": 0.5, "rsi": 55, "mom": 0.2, "dist52": -0.05}
GOOD_Q = quality_detail({"returnOnEquity": 0.2, "profitMargins": 0.15, "debtToEquity": 80, "freeCashflow": 1e9,
                         "revenueGrowth": 0.05, "marketCap": 1e11}, QS)
BAD_Q = quality_detail({"returnOnEquity": 0.01, "profitMargins": -0.02, "debtToEquity": 300, "freeCashflow": -1,
                        "revenueGrowth": -0.1, "marketCap": 1e11}, QS)
LONG = {"pe": 15.0, "pe_pct": 0.2, "pe_median": 20.0, "pe_n": 900, "ret3y": 0.4, "vol": 0.25, "worst_dd": -0.3}


def key(v):
    return (v.v, v.cls, v.line)


def test_missing_inputs_wait_not_enough_history():
    v = entry_verdict({**UP, "rsi": None}, E)
    assert (v.v, v.line) == ("Wait", "Not enough history yet")


def test_stretched_beats_pullback():
    v = entry_verdict({**UP, "rsi": 75, "pct_b": 0.1}, E)
    assert (v.v, v.cls) == ("Stretched", "str")


def test_pullback_in_uptrend():
    v = entry_verdict({**UP, "pct_b": 0.1}, E)
    assert (v.v, v.cls, v.line) == ("Good entry", "good", "Pullback inside an uptrend")
    assert entry_verdict({**UP, "rsi": 38}, E).line == "Pullback inside an uptrend"


def test_steady_uptrend_needs_positive_momentum():
    assert entry_verdict(UP, E).line == "Steady uptrend, nothing stretched"
    assert entry_verdict({**UP, "mom": None}, E).v == "Wait"
    assert entry_verdict({**UP, "mom": -0.1}, E).v == "Wait"


def test_downtrend_and_mixed_wait():
    assert entry_verdict({**UP, "trend": "down"}, E).line == "Trend is down"
    assert entry_verdict({**UP, "trend": "mixed"}, E).line == "No clear trend yet"


def test_entry_reasons_listed():
    v = entry_verdict({**UP, "pct_b": 0.1}, E)
    assert [s for s, _ in v.why][:2] == ["+", "+"] and len(v.why) == 5
    assert all(s in ("+", "–", "·") for s, _ in v.why)


def test_long_percentile_bands():
    assert long_verdict(LONG, "stock", GOOD_Q, QS, L, today=True).v == "Attractive"
    assert long_verdict({**LONG, "pe_pct": 0.5}, "stock", GOOD_Q, QS, L, today=True).v == "Fair"
    assert long_verdict({**LONG, "pe_pct": 0.8}, "stock", GOOD_Q, QS, L, today=True).v == "Expensive"


def test_quality_failure_caps_attractive_at_fair():
    v = long_verdict(LONG, "stock", BAD_Q, QS, L, today=True)
    assert v.v == "Fair" and any(t.startswith("Quality checks fail") for _, t in v.why)


def test_quality_not_judged_is_noted_not_capped():
    thin = quality_detail({"returnOnEquity": 0.2, "profitMargins": 0.15, "debtToEquity": 80}, QS)
    v = long_verdict(LONG, "stock", thin, QS, L, today=True)
    assert v.v == "Attractive" and any("could not be judged" in t for _, t in v.why)


def test_past_day_leaves_quality_out():
    v = long_verdict(LONG, "stock", BAD_Q, QS, L, today=False)
    assert v.v == "Attractive" and v.line == "Below its normal price"
    assert any("today's snapshot" in t for _, t in v.why)


def test_fund_has_no_long_verdict():
    assert long_verdict(LONG, "fund", None, QS, L, today=True) is None


def test_short_pe_history():
    v = long_verdict({**LONG, "pe_n": 503}, "stock", GOOD_Q, QS, L, today=True)
    assert (v.v, v.line) == ("Not enough history", "Not enough P/E history")
    assert long_verdict({**LONG, "pe": None}, "stock", GOOD_Q, QS, L, today=True).line == "Not enough P/E history"


def test_big_3y_run_noted():
    v = long_verdict({**LONG, "ret3y": 1.5}, "stock", GOOD_Q, QS, L, today=True)
    assert any("tend to cool" in t for s, t in v.why if s == "–")


def test_every_verdict_is_in_table_and_never_says_buy():
    table = set(VERDICT_TABLE)
    for t, pb, r, m in itertools.product(["up", "down", "mixed", None], [None, 0.1, 0.5, 0.99], [None, 30, 55, 75], [None, -0.1, 0.2]):
        assert key(entry_verdict({"trend": t, "pct_b": pb, "rsi": r, "mom": m, "dist52": -0.1}, E)) in table
    for pct, n, q, today in itertools.product([None, 0.1, 0.5, 0.9], [100, 900], [GOOD_Q, BAD_Q, None], [True, False]):
        v = long_verdict({**LONG, "pe_pct": pct, "pe": None if pct is None else 15.0, "pe_n": n}, "stock", q, QS, L, today=today)
        assert key(v) in table
    assert not any(re.search(r"\bBuy\b", " ".join(row)) for row in VERDICT_TABLE)


def test_pe_reason_is_the_line_and_no_valuation_claimed():
    v = long_verdict({**LONG, "pe": None, "pe_reason": "earnings reported in another currency"}, "stock", GOOD_Q, QS, L, today=True)
    assert v.v == "Not enough history" and v.line == "P/E not available: earnings reported in another currency"


def test_no_predictive_wording():
    from nordic_desk.explain import EXPLAIN
    text = " ".join(" ".join(r) for r in VERDICT_TABLE) + " " + EXPLAIN["rsi"]["use"] + " " + EXPLAIN["bb"]["use"]
    assert "dip is common" not in text and "often marks" not in text and "squeeze" not in text.lower()


def test_steady_reason_does_not_say_stretched():
    v = entry_verdict({**UP, "pct_b": 0.92}, E)
    assert v.line == "Steady uptrend, nothing stretched"
    assert not any("stretched" in t and "not yet" not in t for _, t in v.why)
