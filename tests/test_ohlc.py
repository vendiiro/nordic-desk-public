import pandas as pd

from nordic_desk.ohlc import load_ohlc, update_ohlc


def frame(start, closes):
    idx = pd.bdate_range(start, periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"open": c - 0.5, "high": c + 1, "low": c - 1, "close": c})


def test_update_then_load_roundtrip(tmp_path):
    df = frame("2026-01-05", [1.5, 2.5, 3.5, 4.5, 5.5])
    st = update_ohlc(["^OMXH25"], root=tmp_path, fetch=lambda t, s: df)
    assert st["^OMXH25"] == "ok"
    out = load_ohlc("^OMXH25", tmp_path)
    assert list(out.columns) == ["open", "high", "low", "close"]
    assert out["close"].iloc[-1] == 5.5 and len(out) == 5


def test_full_refetch_replaces_rescaled_history(tmp_path):
    update_ohlc(["X"], root=tmp_path, fetch=lambda t, s: frame("2026-01-05", [10, 11, 12, 13, 14]))
    seen = []

    def fetch(t, since):
        seen.append(since)
        return frame("2026-01-05", [5, 5.5, 6, 6.5, 7, 7.5])  # whole history rescaled after a split

    update_ohlc(["X"], root=tmp_path, fetch=fetch)
    out = load_ohlc("X", tmp_path)
    assert seen == ["2015-01-01"] and out["close"].tolist() == [5, 5.5, 6, 6.5, 7, 7.5]


def test_missing_file_gives_empty_frame(tmp_path):
    out = load_ohlc("NOPE", tmp_path)
    assert out.empty and list(out.columns) == ["open", "high", "low", "close"]


def test_fetch_error_keeps_old_and_reports(tmp_path):
    update_ohlc(["X"], root=tmp_path, fetch=lambda t, s: frame("2026-01-05", [10, 11]))

    def boom(t, s):
        raise RuntimeError("down")

    st = update_ohlc(["X"], root=tmp_path, fetch=boom)
    assert st["X"].startswith("error:") and len(load_ohlc("X", tmp_path)) == 2


def test_yf_fetch_ohlc_is_split_only_not_dividend_adjusted(monkeypatch):
    import yfinance as yf
    from nordic_desk.ohlc import yf_fetch_ohlc
    seen = {}

    def fake(t, **kw):
        seen.update(kw)
        return frame("2026-01-05", [1.0, 2.0]).rename(columns=str.title)

    monkeypatch.setattr(yf, "download", fake)
    assert yf_fetch_ohlc("X", "2026-01-01")["close"].tolist() == [1.0, 2.0]
    assert seen["auto_adjust"] is False  # dividend-adjusted closes would bias P/E history


def test_shorter_ohlc_refetch_never_cuts_history(tmp_path):
    update_ohlc(["X"], root=tmp_path, fetch=lambda t, s: frame("2020-01-01", list(range(1, 301))))
    st = update_ohlc(["X"], root=tmp_path, fetch=lambda t, s: frame("2023-01-02", [1.0] * 50))
    assert st["X"].startswith("kept stored history") and len(load_ohlc("X", tmp_path)) == 300
