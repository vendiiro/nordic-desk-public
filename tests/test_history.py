import pytest

from nordic_desk.history import alerts, append_snapshot, change_since, previous


def card(t, price, target, share, status, n=20):
    return {"ticker": t, "price": {"close": [price]}, "analysts": {"target_mean": target, "target_low": None, "target_high": None,
            "count": n, "rating_share": share, "status": status}}


def test_snapshot_round_trip_and_replace(tmp_path):
    path = tmp_path / "h.csv"
    append_snapshot(card("AA", 100, 120, 0.5, "between thresholds"), "2026-01-10", path)
    append_snapshot(card("AA", 101, 121, 0.5, "between thresholds"), "2026-01-10", path)   # same day replaces
    append_snapshot(card("AA", 90, 126, 0.6, "below buy threshold"), "2026-01-12", path)
    prev = previous("AA", "2026-01-12", path)
    assert prev["date"] == "2026-01-10" and prev["target_mean"] == 121
    assert previous("AA", "2026-01-10", path) is None
    assert previous("ZZ", "2026-01-12", path) is None


def test_change_since(tmp_path):
    prev = {"date": "2026-01-10", "target_mean": 120.0, "rating_share": 0.5, "status": "between thresholds"}
    ch = change_since(card("AA", 90, 126, 0.6, "below buy threshold"), prev)
    assert ch["since"] == "2026-01-10" and ch["target"] == pytest.approx(0.05)
    assert ch["rating_points"] == pytest.approx(10.0) and ch["status_before"] == "between thresholds"
    assert change_since(card("AA", 90, 126, 0.6, "x"), None) is None


def test_alerts_only_on_crossings():
    cards = {"AA": {"ticker": "AA", "name": "A", "history": {"status_before": "between thresholds"}, "analysts": {"status": "below buy threshold"}},
             "BB": {"ticker": "BB", "name": "B", "history": {"status_before": "below buy threshold"}, "analysts": {"status": "below buy threshold"}},
             "CC": {"ticker": "CC", "name": "C", "history": {"status_before": "between thresholds"}, "analysts": {"status": "above sell threshold"}},
             "DD": {"ticker": "DD", "name": "D", "history": None, "analysts": {"status": "below buy threshold"}}}
    got = alerts(cards)
    assert [(a["ticker"], a["now"]) for a in got] == [("AA", "below buy threshold"), ("CC", "above sell threshold")]


def test_alerts_command(tmp_path, monkeypatch, capsys):
    import json
    from nordic_desk.build import main
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "alerts.json").write_text(json.dumps([{"ticker": "XOM", "name": "Exxon", "now": "above sell threshold",
                                                              "before": "between thresholds"}]), encoding="utf-8")
    main(["alerts"])
    assert "XOM" in capsys.readouterr().out
    (tmp_path / "out" / "alerts.json").write_text("[]", encoding="utf-8")
    main(["alerts"])
    assert "No thresholds crossed" in capsys.readouterr().out


def test_nan_in_file_reads_as_missing():
    from nordic_desk.history import _num
    assert _num("nan") is None and _num("") is None and _num("1.5") == 1.5
