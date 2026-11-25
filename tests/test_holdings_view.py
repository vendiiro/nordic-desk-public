import numpy as np
import pandas as pd
import pytest

from nordic_desk import prices
from nordic_desk.holdings_view import current_weights, render

IDX = pd.bdate_range("2026-01-05", "2026-01-23")


def store(tmp_path, msft_end=2.0):
    root = tmp_path / "prices"
    series = {
        "MSFT": pd.Series(np.linspace(1.0, msft_end, len(IDX)) * 100, index=IDX),   # USD
        "^OMXH25": pd.Series(np.full(len(IDX), 50.0), index=IDX),                  # EUR, flat
        "EURUSD=X": pd.Series(np.full(len(IDX), 1.25), index=IDX),
    }
    for t, s in series.items():
        prices.update([t], root=root, fetch=lambda tk, start, s=s: s)
    return root


def test_weights_sum_to_one_and_keep_cash(tmp_path):
    rows = current_weights("config/holdings.example.toml", price_root=store(tmp_path), end="2026-01-23")
    assert sum(w for _, w in rows) == pytest.approx(1.0)
    assert "Cash" in [n for n, _ in rows]


def test_revalued_from_report_date(tmp_path):
    # example holdings are as of 2026-01-15: MSFT 1800, Suomi 1200, cash 250
    root = store(tmp_path)
    rows = dict(current_weights("config/holdings.example.toml", price_root=root, end="2026-01-23"))
    s = prices.load("MSFT", root=root)
    growth = s.iloc[-1] / s[s.index <= "2026-01-15"].iloc[-1]
    ms = 1800 * growth
    assert rows["Microsoft"] == pytest.approx(ms / (ms + 1200 + 250))


def test_sorted_by_weight(tmp_path):
    rows = current_weights("config/holdings.example.toml", price_root=store(tmp_path), end="2026-01-23")
    ws = [w for _, w in rows]
    assert ws == sorted(ws, reverse=True)


def test_page_shows_only_names_and_weights():
    html = render([("Microsoft", 0.6), ("Cash", 0.4)], close="2026-01-23", report="2026-01-15")
    assert "Microsoft" in html and "60.0%" in html and "40.0%" in html
    assert "€" not in html and "EUR" not in html


def test_all_caps_names_in_sentence_case():
    html = render([("NVIDIA", 1.0)], close="2026-01-23", report="2026-01-15")
    assert ">Nvidia<" in html and "NVIDIA" not in html
