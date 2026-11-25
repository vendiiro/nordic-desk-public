import math

import numpy as np
import pandas as pd
import pytest

from nordic_desk.expected import anchor, combine, signal_piece


def test_anchor_known_rate():
    n = 252 * 2 + 1
    s = pd.Series(np.exp(np.linspace(0, math.log(2), n)), index=pd.bdate_range("2015-01-02", periods=n))
    a = anchor(s)
    assert a["rate"] == pytest.approx(math.sqrt(2) - 1, rel=1e-9) and a["from"] == "2015" and a["to"] == "2016"


def test_anchor_short_none():
    assert anchor(pd.Series(1.0, index=pd.bdate_range("2025-01-01", periods=200))) is None


def test_combine_zero_one_two_pieces():
    assert combine(0.10, None, None) == {"anchor": 0.10, "analyst": None, "signal": None, "combined": 0.10, "pieces": 0}
    assert combine(0.10, 0.20, None)["combined"] == pytest.approx(0.15)
    two = combine(0.10, 0.20, 0.00)
    assert two["combined"] == pytest.approx(0.10) and two["pieces"] == 2


def test_signal_piece_only_with_evidence():
    pooled = {"wait_down": {"mean": -0.03, "reading": "helps"}, "steady": {"mean": 0.02, "reading": "no clear edge"},
              "stretched": {"mean": 0.05, "reading": "works against"}}
    assert signal_piece(0.10, "wait_down", pooled) == pytest.approx(0.07)
    assert signal_piece(0.10, "stretched", pooled) == pytest.approx(0.15)
    assert signal_piece(0.10, "steady", pooled) is None
    assert signal_piece(0.10, "pullback", pooled) is None and signal_piece(0.10, None, pooled) is None
