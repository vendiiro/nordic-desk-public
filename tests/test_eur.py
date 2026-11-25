import json

import numpy as np
import pandas as pd
import pytest

from nordic_desk.config import Instrument
from nordic_desk.eur import asof, currency_of, eur_closes, quote_ok


def s(values, start="2026-01-05"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_usd_converted_with_asof_rate():
    close = s([110.0, 110.0, 110.0])
    fx = s([1.1, 1.1]).drop(pd.Timestamp("2026-01-06"))  # FX missing on day 2
    fx = pd.concat([fx, pd.Series([1.0], index=[pd.Timestamp("2026-01-07")])])
    out = eur_closes(close, "USD", fx)
    assert out.tolist() == pytest.approx([100.0, 100.0, 110.0])


def test_eur_unchanged_and_sek_none():
    close = s([5.0, 6.0])
    assert eur_closes(close, "EUR", s([1.1, 1.1])).tolist() == [5.0, 6.0]
    assert eur_closes(close, "SEK", s([1.1, 1.1])) is None


def test_asof_on_us_holiday():
    spy = s([1.0, 2.0, 3.0]).drop(pd.Timestamp("2026-01-06"))
    out = asof(spy, pd.bdate_range("2026-01-05", periods=3))
    assert out.tolist() == [1.0, 1.0, 3.0]
    assert np.isnan(asof(spy, pd.DatetimeIndex(["2026-01-01"])).iloc[0])


def test_currency_from_fundamentals_then_instruments(tmp_path):
    (tmp_path / "AAA.json").write_text(json.dumps({"currency": "USD", "quote_type": "EQUITY"}), encoding="utf-8")
    inst = {"Fund": Instrument("Fund", "BBB.DE", "EUR", False, "")}
    assert currency_of("AAA", tmp_path, inst) == "USD"
    assert currency_of("BBB.DE", tmp_path, inst) == "EUR"
    assert currency_of("CCC", tmp_path, inst) is None


def test_quote_ok():
    assert quote_ok({"quote_type": "EQUITY"}) and quote_ok({"quote_type": "ETF"}) and quote_ok({"quote_type": "MUTUALFUND"})
    assert not quote_ok({"quote_type": "INDEX"}) and not quote_ok({"quote_type": "CRYPTOCURRENCY"}) and not quote_ok(None)
