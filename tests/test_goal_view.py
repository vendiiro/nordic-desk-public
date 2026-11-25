import re
from datetime import date

import numpy as np

from nordic_desk.goalrange import Goals, simulate
from nordic_desk.views.goal import goal_page, summary_line
from nordic_desk.views.core import nav

META = {"close": "2026-01-14", "eurusd": 1.1, "built": "2026-01-15T07:00Z", "holdings_as_of": "2026-01-10", "skipped": []}


def _goal(goals: Goals, **extra) -> dict:
    rng = np.random.default_rng(4)
    sim = simulate(rng.normal(0.0003, 0.011, 2000), 10_000.0, goals, 0.07, n=500, today=date(2026, 1, 14))
    return {"available": True, "close": "2026-01-14", "value": 10_000.0, "excluded": [], "goals_file": goals.from_file,
            "history_start": "2018-01-02", "history_end": "2026-01-14", "history_years": 7.9,
            "anchor": {"rate": 0.12, "from": "2018", "to": "2026"}, "backtest": None,
            "ledger": {"matured": 0, "held": 0, "pending": 3, "show": False, "by_kind": {}, "first": "2026-01-14"}, **sim} | extra


def _text(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def test_goal_page_with_a_goal():
    g = _goal(Goals(target_eur=20_000, target_year=2031, monthly_eur=100, max_drawdown=0.3, years=5, from_file=True))
    html = goal_page(g, META)
    t = _text(html)
    assert "<h1" in html and "of 10 simulated paths" in t and "€100 a month" in t
    assert 'class="fan big"' in html and 'class="fan small"' in html and html.count('class="band') == 4 and 'class="target"' in html
    assert "Monthly saving for an even chance" in t and "three-in-four" in t
    assert "Not investment advice" in t and "7.0%" in t
    assert not re.search(r"\bwill\b", t, re.I), "no promise wording"
    assert "Goal" in nav("Goal") and 'aria-current="page">Goal<' in html
    assert len(re.findall(r"<tr>", html)) >= 6  # year table: header and one row per year


def test_goal_page_without_goals_file_says_how_to_add_one():
    html = goal_page(_goal(Goals()), META)
    t = _text(html)
    assert "config/goals.local.toml" in t and "no new money" in t and 'class="target"' not in html


def test_long_horizon_note_past_five_years():
    t = _text(goal_page(_goal(Goals(years=8, from_file=True)), META))
    assert "two non-overlapping 5-year spans" in t
    t5 = _text(goal_page(_goal(Goals(years=5, from_file=True)), META))
    assert "non-overlapping 5-year" not in t5


def test_goal_note_and_backtest_and_ledger_lines():
    g = _goal(Goals(target_eur=20_000, target_year=2045, years=3, from_file=True),
              backtest={"n": 60, "inside_90": 0.85, "inside_50": 0.47, "p_90": 0.2, "p_50": 0.6, "n_independent": 5,
                        "start": "2021-01-04", "end": "2026-01-14"},
              ledger={"matured": 6, "held": 5, "pending": 2, "show": True, "first": "2025-12-01",
                      "by_kind": {"goal_1y": {"matured": 4, "held": 3}, "risk_21d": {"matured": 2, "held": 2}}})
    t = _text(goal_page(g, META))
    assert "at most 10 years" in t and "85%" in t and "60 month starts" in t
    assert "3 of 4 one-year ranges" in t and "2 of 2 next-month ranges" in t
    assert re.search(r">20(31|32)<", goal_page(_goal(Goals(years=5, from_file=True)), META))  # the last year is labelled


def test_unavailable_goal_page():
    t = _text(goal_page({"available": False, "why": "Only the excluded test positions are held."}, META))
    assert "Only the excluded test positions are held." in t


def test_summary_line_for_today():
    g = _goal(Goals(target_eur=20_000, target_year=2031, years=5, from_file=True))
    s = summary_line(g)
    assert "of 10" in s and "2031" in s
    assert summary_line({"available": False, "why": "x"}) is None
