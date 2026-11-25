import json

import numpy as np
import pandas as pd
import pytest

from nordic_desk import prices
from nordic_desk.build import build

WATCH = ["AAPL", "MSFT", "XOM"]


@pytest.fixture
def built(tmp_path):
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2024-06-03", "2026-01-14")
    root = tmp_path / "prices"
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0004, 0.015, len(idx))) for t in WATCH + ["SPY", "^OMXH25"]}
    data["EURUSD=X"] = 1.1 + 0.01 * np.sin(np.arange(len(idx)) / 20)
    for t, v in data.items():
        prices.update([t], root=root, fetch=lambda tk, start, v=v: pd.Series(v, index=idx))
    out = tmp_path / "out"
    build(end="2026-01-14", price_root=root, holdings_path="config/holdings.example.toml", watchlist=WATCH, out_dir=out)
    return (json.loads((out / "desk.json").read_text(encoding="utf-8")),
            json.loads((out / "aamu.json").read_text(encoding="utf-8")), out)


@pytest.fixture(autouse=True)
def no_fund_network(monkeypatch):
    """Tests never reach Yahoo for fund holdings: every ticker reads as 'not a fund' unless a test passes a fetcher."""
    def stub(t):
        raise LookupError("no fund data")
    monkeypatch.setattr("nordic_desk.lookthrough.yf_top_holdings", stub)
