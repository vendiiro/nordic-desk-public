import numpy as np
import pandas as pd
import pytest

from nordic_desk.panel import eur_panel, to_eur


def bseries(start, n, base=100.0, step=1.0, name=None):
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(base + step * np.arange(n), index=idx, name=name, dtype=float)


def test_usd_converted():
    px = pd.Series([100.0], index=pd.to_datetime(["2024-03-01"]))
    fx = pd.Series([1.25], index=pd.to_datetime(["2024-03-01"]))
    assert to_eur(px, fx, "USD").iloc[0] == pytest.approx(80.0)
    assert to_eur(px, fx, "EUR").iloc[0] == 100.0


def test_usd_uses_last_known_rate():
    px = pd.Series([100.0, 100.0], index=pd.to_datetime(["2024-03-01", "2024-03-04"]))
    fx = pd.Series([1.25], index=pd.to_datetime(["2024-03-01"]))
    assert to_eur(px, fx, "USD").tolist() == pytest.approx([80.0, 80.0])


def test_holiday_forward_filled():
    us = bseries("2024-01-01", 300, name="US")
    fi = bseries("2024-01-01", 300, name="FI").drop(pd.Timestamp("2024-12-06"))
    fx = bseries("2024-01-01", 300, base=1.0, step=0.0)
    p = eur_panel({"US": us, "FI": fi}, {"US": "EUR", "FI": "EUR"}, fx, end="2025-02-21", n_returns=252)
    assert not p.isna().any().any()
    assert p.loc["2024-12-06", "FI"] == p.loc["2024-12-05", "FI"]


def test_window_length():
    s = bseries("2023-01-02", 400, name="A")
    fx = bseries("2023-01-02", 400, base=1.0, step=0.0)
    p = eur_panel({"A": s}, {"A": "USD"}, fx, end="2024-06-28", n_returns=252)
    assert len(p) == 253
    assert p.index[-1] <= pd.Timestamp("2024-06-28")


def test_weekend_crypto_dropped():
    eth = pd.Series(np.arange(400, dtype=float) + 1, index=pd.date_range("2023-06-01", periods=400), name="ETH")
    a = bseries("2023-06-01", 300, name="A")
    fx = bseries("2023-06-01", 300, base=1.0, step=0.0)
    p = eur_panel({"ETH": eth, "A": a}, {"ETH": "EUR", "A": "EUR"}, fx, end="2024-06-28", n_returns=200)
    assert (p.index.day_of_week < 5).all()


def test_short_history_named():
    a = bseries("2023-01-02", 400, name="A")
    young = bseries("2024-05-01", 30, name="YOUNG")
    fx = bseries("2023-01-02", 400, base=1.0, step=0.0)
    with pytest.raises(ValueError, match="YOUNG"):
        eur_panel({"A": a, "YOUNG": young}, {"A": "EUR", "YOUNG": "EUR"}, fx, end="2024-06-14", n_returns=252)


def test_other_currency_uses_its_rate():
    px = pd.Series([110.0], index=pd.to_datetime(["2024-03-01"]))
    sek = pd.Series([11.0], index=pd.to_datetime(["2024-03-01"]))   # SEK per EUR
    assert to_eur(px, sek, "SEK").iloc[0] == pytest.approx(10.0)


def test_panel_takes_rates_for_other_currencies():
    a = bseries("2023-01-02", 400, name="A")
    fx = bseries("2023-01-02", 400, base=1.0, step=0.0)
    sek = bseries("2023-01-02", 400, base=10.0, step=0.0)
    p = eur_panel({"A": a}, {"A": "SEK"}, fx, end="2024-06-28", rates={"SEK": sek})
    assert p["A"].iloc[-1] == pytest.approx(a[a.index <= "2024-06-28"].iloc[-1] / 10)
    with pytest.raises(ValueError, match="SEK"):
        eur_panel({"A": a}, {"A": "SEK"}, fx, end="2024-06-28")
