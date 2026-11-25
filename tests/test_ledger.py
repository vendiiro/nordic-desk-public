import json

import numpy as np
import pandas as pd
import pytest

from nordic_desk import ledger


def _row(made="2026-01-05", kind="goal_1y", days=3, q=None, w=None):
    return ledger.make_row(made, kind, days, q or {"0.05": -0.1, "0.5": 0.0, "0.95": 0.1}, drift=0.07, weights=w or {"A": 0.5})


def test_make_row_keys_by_kind_and_week():
    r = _row()
    assert r["week"] == "2026-W02" and r["kind"] == "goal_1y" and r["scored"] is None and len(r["hash"]) == 12


def test_record_keeps_one_row_per_kind_per_week(tmp_path):
    p = tmp_path / "ledger" / "forecasts.jsonl"
    assert ledger.record(p, [_row("2026-01-05"), _row("2026-01-05", "risk_21d")]) == 2
    assert ledger.record(p, [_row("2026-01-07"), _row("2026-01-12")]) == 1  # same week, then a new week
    rows = ledger.read(p)
    assert [(r["kind"], r["made"]) for r in rows] == [("goal_1y", "2026-01-05"), ("risk_21d", "2026-01-05"), ("goal_1y", "2026-01-12")]


def _panel():
    idx = pd.bdate_range("2026-01-05", periods=6)
    return pd.DataFrame({"A": [100.0, 101, 102, 110, 111, 112], "B": [50.0, 50, 50, 25, 25, 25]}, index=idx)


def test_score_waits_for_maturity_then_scores_with_its_own_weights(tmp_path):
    p = tmp_path / "f.jsonl"
    ledger.record(p, [_row("2026-01-05", days=3, w={"A": 0.5, "B": 0.25}), _row("2026-01-08", "risk_21d", days=10)])
    assert ledger.score(p, _panel()) == 1
    a, b = ledger.read(p)
    # three trading days after 5 Jan is 8 Jan: A +10%, B -50%
    assert a["scored"]["end"] == "2026-01-08"
    assert a["scored"]["realised"] == pytest.approx(0.5 * 0.10 + 0.25 * -0.5)
    assert a["scored"]["inside"] is True  # -7.5% falls inside the -10%..+10% band
    assert a["scored"]["pinball"] == pytest.approx(ledger.pinball(a["q"], -0.075))
    assert b["scored"] is None
    assert ledger.score(p, _panel()) == 0  # scored rows are not scored again


def test_pinball_loss():
    q = {"0.05": -0.1, "0.5": 0.0, "0.95": 0.1}
    # y = 0.2: 0.05*0.3 + 0.5*0.2 + 0.95*0.1
    assert ledger.pinball(q, 0.2) == pytest.approx((0.015 + 0.1 + 0.095) / 3)


def test_summary_shows_a_record_only_from_five_matured_rows():
    rows = [dict(_row(), scored={"inside": i != 0, "pinball": 0.01, "end": "x", "realised": 0.0}) for i in range(4)]
    s = ledger.summary(rows + [_row()])
    assert s["matured"] == 4 and s["held"] == 3 and s["show"] is False and s["pending"] == 1
    s = ledger.summary(rows + [dict(rows[0])])
    assert s["matured"] == 5 and s["show"] is True and s["by_kind"]["goal_1y"] == {"matured": 5, "held": 3}
