import pandas as pd

from nordic_desk import prices


def series(start, n, name="X", base=100.0):
    idx = pd.bdate_range(start, periods=n)
    return pd.Series([base + i for i in range(n)], index=idx, name=name, dtype=float)


class FakeFetch:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def __call__(self, ticker, start):
        self.calls.append((ticker, start))
        s = self.data.get(ticker, pd.Series(dtype=float, index=pd.DatetimeIndex([])))
        return s[s.index >= pd.Timestamp(start)]


def test_update_writes_new_file(tmp_path):
    fake = FakeFetch({"AAPL": series("2024-01-01", 10)})
    status = prices.update(["AAPL"], root=tmp_path, fetch=fake)
    assert status == {"AAPL": "ok"}
    s = prices.load("AAPL", root=tmp_path)
    assert len(s) == 10 and s.iloc[0] == 100.0
    assert fake.calls == [("AAPL", "2015-01-01")]


def test_update_refetches_full_history_so_splits_and_dividends_stay_consistent(tmp_path):
    fake = FakeFetch({"AAPL": series("2024-01-01", 20)})
    prices.update(["AAPL"], root=tmp_path, fetch=fake)
    fake.data["AAPL"] = series("2024-01-01", 25) / 2  # after a 2:1 split Yahoo rescales the whole past
    prices.update(["AAPL"], root=tmp_path, fetch=fake)
    assert fake.calls == [("AAPL", "2015-01-01"), ("AAPL", "2015-01-01")]
    s = prices.load("AAPL", root=tmp_path)
    assert len(s) == 25 and s.iloc[0] == 50.0 and s.index.is_unique  # old unadjusted rows replaced, not merged


def test_empty_refetch_keeps_stored_history(tmp_path):
    fake = FakeFetch({"AAPL": series("2024-01-01", 10)})
    prices.update(["AAPL"], root=tmp_path, fetch=fake)
    fake.data["AAPL"] = series("2024-01-01", 0)
    st = prices.update(["AAPL"], root=tmp_path, fetch=fake)
    assert st["AAPL"].startswith("no new data") and len(prices.load("AAPL", root=tmp_path)) == 10


def test_empty_ticker_reported(tmp_path):
    fake = FakeFetch({"AAPL": series("2024-01-01", 5)})
    status = prices.update(["NOPE", "AAPL"], root=tmp_path, fetch=fake)
    assert status == {"NOPE": "empty", "AAPL": "ok"}
    assert prices.load("NOPE", root=tmp_path).empty
    assert not list(tmp_path.glob("NOPE*"))


def test_fetch_error_reported(tmp_path):
    def boom(ticker, start):
        raise RuntimeError("network down")
    status = prices.update(["AAPL"], root=tmp_path, fetch=boom)
    assert status["AAPL"].startswith("error: ") and "network down" in status["AAPL"]


def test_filename_safe(tmp_path):
    fake = FakeFetch({"^OMXH25": series("2024-01-01", 3), "EURUSD=X": series("2024-01-01", 3, base=1.1)})
    prices.update(["^OMXH25", "EURUSD=X"], root=tmp_path, fetch=fake)
    assert len(prices.load("^OMXH25", root=tmp_path)) == 3
    assert prices.load("EURUSD=X", root=tmp_path).name == "EURUSD=X"
    assert all("^" not in p.name and "=" not in p.name for p in tmp_path.iterdir())


def test_stale_ticker_reported(tmp_path):
    fake = FakeFetch({"OLD": series("2024-01-01", 5)})
    prices.update(["OLD"], root=tmp_path, fetch=fake)
    fake.data["OLD"] = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    status = prices.update(["OLD"], root=tmp_path, fetch=fake)
    assert status["OLD"] == "no new data (last 2024-01-05)"


def test_shorter_refetch_never_cuts_history(tmp_path):
    fake = FakeFetch({"AAPL": series("2020-01-01", 300)})
    prices.update(["AAPL"], root=tmp_path, fetch=fake)
    fake.data["AAPL"] = series("2023-01-02", 50)
    st = prices.update(["AAPL"], root=tmp_path, fetch=fake)
    assert st["AAPL"].startswith("kept stored history") and len(prices.load("AAPL", root=tmp_path)) == 300


def test_refetch_starts_at_the_stored_first_date(tmp_path):
    fake = FakeFetch({"AAPL": series("2012-01-02", 30)})
    prices.update(["AAPL"], start="2012-01-01", root=tmp_path, fetch=fake)
    prices.update(["AAPL"], root=tmp_path, fetch=fake)  # default start is 2015, but the store goes back to 2012
    assert fake.calls[-1] == ("AAPL", "2012-01-02") and len(prices.load("AAPL", root=tmp_path)) == 30


def test_refetch_ending_early_keeps_newest_rows(tmp_path):
    fake = FakeFetch({"AAPL": series("2024-01-01", 30)})
    prices.update(["AAPL"], root=tmp_path, fetch=fake)
    fake.data["AAPL"] = series("2024-01-01", 20)  # Yahoo lagging: ends 10 days early
    st = prices.update(["AAPL"], root=tmp_path, fetch=fake)
    assert st["AAPL"].startswith("kept stored history") and len(prices.load("AAPL", root=tmp_path)) == 30
